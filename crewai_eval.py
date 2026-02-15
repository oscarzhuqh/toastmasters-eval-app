"""CrewAI evaluation generator for Toastmasters Evaluation Assistant (T.E.A.).

Key goals:
- Robust generation: works with CrewAI when available; falls back to a single LLM call.
- Meeting-ready output: markdown structured in a way that can be exported into a form-like PDF/HTML layout.

App expects:
    from crewai_eval import run_crewai_eval

Optional helper (used by reports / screenshots):
    from crewai_eval import purpose_alignment_summary
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Tuple


def _get_setting(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first (if available), else env."""
    value = ""
    try:
        import streamlit as st  # type: ignore

        if hasattr(st, "secrets") and key in st.secrets:
            value = str(st.secrets[key]).strip()
    except Exception:
        pass

    if not value:
        value = str(os.getenv(key, default)).strip()

    return value


def _fallback_llm(prompt: str, api_key: str, model: str) -> str:
    """Fallback using the OpenAI Python SDK (if installed)."""
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)

        # Prefer Responses API if available
        try:
            resp = client.responses.create(
                model=model,
                input=prompt,
            )
            text = getattr(resp, "output_text", None)
            if text:
                return str(text).strip()
            return str(resp).strip()
        except Exception:
            # Older: Chat Completions API
            chat = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Toastmasters speech evaluation assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            return (chat.choices[0].message.content or "").strip()

    except Exception as e:
        return (
            "CrewAI failed and OpenAI fallback also failed.\n\n"
            f"Fallback error: {e}\n\n"
            "Tip: Ensure OPENAI_API_KEY is set in Streamlit secrets or environment variables."
        )


def purpose_alignment_summary(md_text: str) -> str:
    """Lightweight summary extractor used for reports/snapshots.

    Returns a short 1–2 sentence summary if a Purpose Alignment section exists,
    else returns an empty string.

    This keeps the app flexible: your export layout can place this summary near the checkbox block.
    """
    md = (md_text or "").strip()
    if not md:
        return ""

    # Find "Purpose Alignment" section (allow # / ##)
    m = re.search(r"^#{1,3}\s+Purpose\s+Alignment\s*$", md, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""

    section = md[m.end():]
    section = re.split(r"^#{1,3}\s+", section, maxsplit=1, flags=re.MULTILINE)[0].strip()
    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]

    # Return first 1–2 non-checklist lines
    out = []
    for ln in lines:
        if re.match(r"^-\s*\[(x| )\]\s+", ln, flags=re.IGNORECASE):
            break
        if ln.startswith("-"):
            continue
        out.append(ln)
        if len(out) >= 2:
            break
    return " ".join(out).strip()


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
    speaker_name: str = "",
    evaluator_name: str = "",
    meeting_date: str = "",
    speech_title: str = "",
    total_score: Optional[int] = None,
    score_band: str = "",
    **_ignored: object,
) -> str:
    """Generate an editable evaluation draft (Markdown).

    Returns a single markdown string.

    Extra keyword args are accepted for forward-compatibility with the Streamlit app.
    """

    api_key = _get_setting("OPENAI_API_KEY", "")
    model = _get_setting("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return (
            "❌ Missing OPENAI_API_KEY.\n\n"
            "Add it in Streamlit secrets (recommended):\n"
            "- Streamlit Cloud: App → Settings → Secrets\n"
            "- Local: create .streamlit/secrets.toml\n\n"
            "Example secrets.toml:\n"
            "OPENAI_API_KEY = \"sk-...\"\n"
            "OPENAI_MODEL = \"gpt-4o-mini\"\n"
        )

    score_line = ""
    if total_score is not None:
        score_line = f"- Total competency score (rubric): {total_score}" + (f" ({score_band})" if score_band else "")

    prompt = f"""
You are the Toastmasters Evaluation Assistant (T.E.A.).

Goal:
Turn the evaluator's rubric ratings + rough notes into a clear, kind, and project-aligned evaluation draft
that is suitable for a real Toastmasters club meeting.

Meeting details:
- Speaker: {speaker_name or "(not provided)"}
- Evaluator: {evaluator_name or "(not provided)"}
- Date: {meeting_date or "(not provided)"}
- Speech Title: {speech_title or "(not provided)"}
{score_line}

Pathways context:
- Pathway: {pathway}
- Level: {level}
- Project: {project}
- Project Purpose: {purpose}
- Level Focus: {level_focus}
- Target speech length: {speech_len}

Evaluation criteria reference (for the evaluator to stay consistent):
{criteria_text.strip() or "(No criteria text provided)"}

Evaluator input (rubric summary + comments + general notes):
{notes}

Write the output as a structured evaluation draft in plain English.

Required structure (use Markdown headings exactly):
## Opening
(1–2 sentences that reference the project purpose)

## Strengths
- Bullet points that map back to rubric strengths and notes

## Recommendations
- Bullet points that map back to rubric improvement areas and notes

## One Challenge
(1–2 sentences, very actionable)

## Purpose Alignment
- 1–2 sentence summary of how the speech aligns to Purpose + Level focus.
- Checkbox checklist (Markdown task list):
  - [ ] Purpose clearly addressed
  - [ ] Level focus demonstrated
  - [ ] Feedback linked to evaluation criteria
  - [ ] Balanced commendations + improvements
  - [ ] Actionable next step provided
- 2–3 short bullets explaining why items are checked/unchecked.

Rules:
- Be specific (use examples where available), but do not invent details.
- If details are missing, use "Based on the notes provided..." and keep it general.
- Tone: supportive, respectful, Toastmasters-appropriate.
- Output Markdown only. No tables unless necessary.
""".strip()

    # --- Try CrewAI ---
    try:
        from crewai import Agent, Task, Crew, Process  # type: ignore

        llm = None
        try:
            from crewai import LLM  # type: ignore

            llm = LLM(model=model, api_key=api_key)
        except Exception:
            llm = None

        evaluator = Agent(
            role="Speech Evaluator",
            goal="Write a clear, supportive Toastmasters evaluation draft aligned to Pathways project goals.",
            backstory="You are a seasoned Toastmasters evaluator who focuses on actionable feedback.",
            llm=llm,
            verbose=False,
        )

        alignment = Agent(
            role="Alignment Checker",
            goal="Ensure the draft explicitly aligns to Project Purpose and Level Focus.",
            backstory="You ensure evaluations are objective, rubric-aligned, and project-relevant.",
            llm=llm,
            verbose=False,
        )

        draft_task = Task(
            description=prompt,
            expected_output="A complete markdown evaluation draft following the required structure.",
            agent=evaluator,
        )

        check_task = Task(
            description=(
                "Review the evaluation draft and ensure headings match exactly: "
                "Opening, Strengths, Recommendations, One Challenge, Purpose Alignment. "
                "Repair the Purpose Alignment checklist if missing. Keep Markdown only."
            ),
            expected_output="The improved final markdown draft.",
            agent=alignment,
            context=[draft_task],
        )

        crew = Crew(
            agents=[evaluator, alignment],
            tasks=[draft_task, check_task],
            process=Process.sequential,
            verbose=False,
        )

        result = crew.kickoff()

        if isinstance(result, str):
            return result.strip()
        for attr in ("raw", "output", "final_output"):
            if hasattr(result, attr):
                value = getattr(result, attr)
                if value:
                    return str(value).strip()
        return str(result).strip()

    except Exception:
        return (
            _fallback_llm(prompt, api_key=api_key, model=model)
            + "\n\n---\n"
            + "*(Note: CrewAI failed in this environment, so the app used a direct LLM fallback.)*"
        )
