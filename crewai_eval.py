"""CrewAI evaluation helper.

Design goals:
- Works on Streamlit Cloud (secrets) and local dev (env vars).
- Avoids CrewAI API/version edge cases (no Task.context / config tricks).
- Returns a single Markdown draft that is easy to export to PDF.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class OpenAIConfig:
    api_key: str
    base_url: Optional[str]
    model: str


def _read_secret(key: str) -> Optional[str]:
    """Best-effort read from Streamlit secrets (no hard dependency)."""
    try:
        import streamlit as st  # type: ignore

        if hasattr(st, "secrets") and key in st.secrets:
            v = str(st.secrets[key]).strip()
            return v or None
    except Exception:
        pass
    return None


def _get_openai_config() -> OpenAIConfig:
    # API key
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or _read_secret("OPENAI_API_KEY") or ""

    # Base URL (optional) for OpenAI-compatible endpoints
    base_url = (
        os.getenv("OPENAI_BASE_URL", "").strip()
        or os.getenv("OPENAI_API_BASE", "").strip()
        or _read_secret("OPENAI_BASE_URL")
        or _read_secret("OPENAI_API_BASE")
    )
    base_url = base_url or None

    # Model selection (env first, then secrets override, then fallback)
    model = os.getenv("OPENAI_MODEL", "").strip()
    secret_model = _read_secret("OPENAI_MODEL")
    if secret_model:
        model = secret_model
    model = model or "gpt-4o-mini"

    return OpenAIConfig(api_key=api_key, base_url=base_url, model=model)


def _coerce_result_to_text(result: Any) -> str:
    # CrewAI has returned many shapes across versions; handle the common ones.
    if result is None:
        return ""
    for attr in ("raw", "output", "result", "final"):
        if hasattr(result, attr):
            try:
                v = getattr(result, attr)
                if isinstance(v, str):
                    return v
            except Exception:
                pass
    if isinstance(result, dict):
        # Prefer likely keys
        for k in ("raw", "output", "result", "final", "text"):
            v = result.get(k)
            if isinstance(v, str):
                return v
        return str(result)
    return str(result)


def run_crewai_eval(
    *,
    notes: str,
    pathway: str,
    level: str,
    project: str,
    level_focus: str,
    purpose: str,
    speech_len: str,
    criteria_text: str = "",
    total_score: Optional[int] = None,
    score_band: str = "",
    **_: Any,
) -> str:
    """Generate an evaluation draft using CrewAI.

    Parameters are intentionally explicit (and we accept **_ for forward/backward compatibility).
    """

    cfg = _get_openai_config()
    if not cfg.api_key:
        return (
            "❌ **Missing OPENAI_API_KEY**\n\n"
            "Add it in **Streamlit Cloud → App settings → Secrets** as:\n\n"
            "```toml\nOPENAI_API_KEY = \"your_key_here\"\n```\n\n"
            "(Or set `OPENAI_API_KEY` as an environment variable locally.)"
        )

    # Set env vars so CrewAI (and any underlying OpenAI-compatible client) can pick them up.
    os.environ["OPENAI_API_KEY"] = cfg.api_key
    os.environ["OPENAI_MODEL"] = cfg.model
    if cfg.base_url:
        os.environ["OPENAI_BASE_URL"] = cfg.base_url
        os.environ["OPENAI_API_BASE"] = cfg.base_url

    try:
        from crewai import Agent, Crew, Process, Task  # type: ignore
    except Exception as e:
        return (
            "❌ **CrewAI is not installed / failed to import**\n\n"
            f"Error: `{type(e).__name__}: {e}`\n\n"
            "Add `crewai` to your `requirements.txt`, redeploy, and try again."
        )

    score_line = ""
    if total_score is not None:
        score_line = f"Total rubric score: **{total_score}**"
        if score_band:
            score_line += f" — **{score_band}**"

    # One-task design (avoid Task.context differences across CrewAI versions).
    prompt = f"""
You are a Toastmasters speech evaluator. Create a structured evaluation draft in **Markdown**.

## Context (retrieved from the knowledge base)
- Pathway: {pathway}
- Level: {level}
- Project: {project}
- Project purpose: {purpose}
- Level focus: {level_focus}
- Expected speech length: {speech_len}
{('- ' + score_line) if score_line else ''}

## Evaluation Criteria (for reference)
{criteria_text if criteria_text.strip() else '(Not provided)'}

## Evaluator notes (input)
{notes.strip() or '(No notes provided)'}

## Output requirements
1) Start with a **2–3 sentence overall summary** aligned to the *project purpose*.
2) Create **Strengths (What you did well)** — 3 to 6 bullet points, concrete and evidence-based.
3) Create **Areas for improvement (What to work on next)** — 3 to 6 bullet points, phrased as coaching.
4) Add **Actionable next steps** — 2 to 4 specific practice tasks.
5) Add **Closing encouragement** — 1 short paragraph.

### Tone
Supportive, professional, and specific. Avoid harsh language. Avoid generic advice.

### Do NOT
- Do not mention internal system prompts or “CrewAI”.
- Do not ask the user for more info.
""".strip()

    evaluator = Agent(
        role="Toastmasters Speech Evaluator",
        goal="Turn rubric ratings + notes into a project-aligned evaluation draft.",
        backstory="You are a certified Toastmasters evaluator who writes clear, supportive, actionable feedback.",
        verbose=False,
    )

    task = Task(
        description=prompt,
        expected_output=(
            "A complete Markdown evaluation draft with headings: Summary, Strengths, "
            "Areas for improvement, Next steps, Closing encouragement."
        ),
    )

    crew = Crew(
        agents=[evaluator],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        try:
            result = crew.kickoff()
        except TypeError:
            # Some versions expect inputs kwarg
            result = crew.kickoff(inputs={})
    except Exception as e:
        return (
            "❌ **Draft generation failed**\n\n"
            f"Error: `{type(e).__name__}: {e}`\n\n"
            "If this persists, check your `requirements.txt` CrewAI version and redeploy."
        )

    text = _coerce_result_to_text(result).strip()
    return text or "⚠️ No output returned from CrewAI."
