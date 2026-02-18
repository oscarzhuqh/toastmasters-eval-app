"""CrewAI evaluation generator for Toastmasters Evaluation Assistant (T.E.A.).

Designed to be robust:
- Reads API key/model from env vars or Streamlit secrets.
- Attempts to use CrewAI.
- If CrewAI isn't available or fails due to version mismatches, falls back to a single LLM call.

App expects:
    from crewai_eval import run_crewai_eval
"""

from __future__ import annotations

import os
import traceback
from typing import Optional


def _get_setting(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first (if available), else env."""
    value = ""

    # Streamlit secrets (works on Streamlit Cloud and locally with .streamlit/secrets.toml)
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

        # Newer SDKs: Responses API
        try:
            resp = client.responses.create(
                model=model,
                input=prompt,
            )
            # `output_text` is a convenience on newer SDKs
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
) -> str:
    """Generate an editable evaluation draft.

    Returns a single markdown string.
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

    prompt = f"""
You are the Toastmasters Evaluation Assistant (T.E.A.).

Goal:
Turn the evaluator's rubric ratings + rough notes into a clear, kind, and project-aligned evaluation draft.

Meeting details:
- Speaker: {speaker_name or "(not provided)"}
- Evaluator: {evaluator_name or "(not provided)"}
- Date: {meeting_date or "(not provided)"}
- Speech Title: {speech_title or "(not provided)"}

Pathways context:
- Pathway: {pathway}
- Level: {level}
- Project: {project}
- Project Purpose: {purpose}
- Level Focus: {level_focus}
- Speech length target: {speech_len}

Evaluation criteria reference (for the evaluator to stay consistent):
{criteria_text.strip() or "(No criteria text provided)"}

Evaluator input (rubric summary + comments + general notes):
{notes}

Write the output as a structured evaluation draft in plain English.

Required structure:
1) **Opening** (1–2 sentences) that references the selected project purpose.
2) **Rubric Snapshot (1–5)**: list *every* criterion with rating and (if provided) evaluator comment in this exact format:
   - <Criterion>: <rating>/5 — <short comment or "No comment">
3) **Strengths (4–5)**: bullets that reference specific criteria and ratings (e.g., "Clarity (4/5)…").
4) **Areas for Improvement (1–3)**: bullets that reference specific criteria and ratings.
5) **One Challenge**: one actionable next step (1–2 sentences).
6) **Purpose Alignment (Evidence-Bound)**:
   - Alignment claim: <one sentence>
   - Evidence: <quote or paraphrase from evaluator notes/rubric comment>
   - Alignment claim: <one sentence>
   - Evidence: <quote or paraphrase from evaluator notes/rubric comment>
   (Include 2–3 claim/evidence pairs. If evidence is insufficient, write exactly: "Insufficient evidence: no Evidence lines were provided in the evaluator inputs.")
7) **Evaluator Alignment Checklist** (NOT auto-ticked): output as plain text checklist:
   - [ ] Purpose clearly addressed
   - [ ] Level focus demonstrated
   - [ ] Feedback linked to evaluation criteria
   - [ ] Balanced commendations + improvements
   - [ ] Actionable next step provided



Rules:
- Be specific (use examples where available), but do not invent details.
- If details are missing, use "Based on the notes provided..." and keep it general.
- Keep tone supportive and Toastmasters-appropriate.
- Output Markdown only.
""".strip()

    # --- Try CrewAI ---
    try:
        from crewai import Agent, Task, Crew, Process  # type: ignore

        # Some CrewAI versions provide an LLM helper. We'll try it, but degrade gracefully.
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
            llm=llm,  # if None, CrewAI may still read env vars
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
                "Review the evaluation draft and add/repair the 'Alignment check' section so it clearly "
                "links to Project Purpose + Level focus. Keep everything concise and Markdown only."
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
        # CrewAI may return a string or an object
        if isinstance(result, str):
            return result.strip()
        # common attributes
        for attr in ("raw", "output", "final_output"):
            if hasattr(result, attr):
                value = getattr(result, attr)
                if value:
                    return str(value).strip()
        return str(result).strip()

    except Exception:
        # --- Fallback ---
        return (
            _fallback_llm(prompt, api_key=api_key, model=model)
            + "\n\n---\n"
            + "*(Note: CrewAI failed in this environment, so the app used a direct LLM fallback.)*"
        )
