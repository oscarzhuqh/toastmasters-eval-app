# crewai_eval.py
from __future__ import annotations

import os
from typing import Optional

from crewai import Agent, Task, Crew, Process


def _get_streamlit_secret(key: str) -> Optional[str]:
    """Safely read Streamlit secrets if running in Streamlit; otherwise return None."""
    try:
        import streamlit as st  # type: ignore

        if hasattr(st, "secrets") and key in st.secrets:
            val = str(st.secrets[key]).strip()
            return val or None
    except Exception:
        pass
    return None


def _get_api_key() -> Optional[str]:
    """
    Tries (in order):
      1) Streamlit secrets: OPENAI_API_KEY
      2) Environment variable: OPENAI_API_KEY
    """
    key = _get_streamlit_secret("OPENAI_API_KEY")
    if key:
        return key

    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key or None


def _get_model_name() -> str:
    """
    Tries (in order):
      1) Environment variable: OPENAI_MODEL (can be blank)
      2) Streamlit secrets: OPENAI_MODEL
      3) Fallback: gpt-4o-mini
    """
    # Start with env (blank allowed)
    model = os.getenv("OPENAI_MODEL", "").strip()

    # Streamlit secrets can override model too
    secret_model = _get_streamlit_secret("OPENAI_MODEL")
    if secret_model:
        model = secret_model

    return model or "gpt-4o-mini"


def _make_llm():
    """
    Creates an LLM object compatible with CrewAI.

    Works across common setups:
      - If your CrewAI supports `crewai.LLM`, use it.
      - Otherwise, set env vars so provider wrappers can still work.

    Required:
      OPENAI_API_KEY (Streamlit Secrets or env var)
    Optional:
      OPENAI_MODEL (Streamlit Secrets or env var)
    """
    api_key = _get_api_key()
    model = _get_model_name()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Add it to Streamlit Secrets or set it as an environment variable."
        )

    # Prefer CrewAI's LLM helper if available
    try:
        from crewai import LLM  # type: ignore

        return LLM(model=model, api_key=api_key)
    except Exception:
        # Fallback: some setups let CrewAI/provider libs read env vars directly
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_MODEL"] = model
        return None


def run_crewai_eval(
    *,
    notes: str,
    pathway: str,
    level: str,
    project: str,
    level_focus: str,
    purpose: str,
    speech_len: str,
) -> str:
    """
    Returns a structured Toastmasters evaluation draft in Markdown.

    Streamlit app should pass:
      - notes (includes rubric summary + your general comments)
      - pathway, level, project, level_focus, purpose, speech_len
    """
    llm = _make_llm()

    context = f"""
Toastmasters context (from knowledge base):
- Pathway: {pathway}
- Level: {level}
- Project: {project}
- Level focus: {level_focus}
- Purpose: {purpose}
- Speech length: {speech_len}

Evaluator input (do NOT invent extra observations beyond these notes):
{notes}
""".strip()

    # -------------------- AGENTS --------------------
    draft_agent = Agent(
        role="Toastmasters Evaluation Drafter",
        goal=(
            "Draft a clear, supportive, and specific evaluation aligned to the project purpose "
            "and level focus, using only the evaluator notes and rubric summary."
        ),
        backstory=(
            "You are an experienced Toastmasters evaluator. You write constructive feedback that is "
            "actionable, kind, and aligned to the evaluation criteria and the speaker’s project objectives."
        ),
        allow_delegation=False,
        verbose=False,
        llm=llm,
    )

    checker_agent = Agent(
        role="Alignment Checker",
        goal=(
            "Check the draft for alignment to the project purpose, level focus, and rubric summary. "
            "Ensure the draft is specific and does not hallucinate."
        ),
        backstory=(
            "You verify quality and alignment. You flag vague claims, missing links to the rubric, "
            "and any invented details not supported by the evaluator notes."
        ),
        allow_delegation=False,
        verbose=False,
        llm=llm,
    )

    # -------------------- TASKS --------------------
    draft_task = Task(
        description=(
            "Write a Toastmasters evaluation draft in MARKDOWN with these sections:\n\n"
            "1) Header block (Speaker / Evaluator / Date if present in notes)\n"
            "2) Overall summary (2–4 sentences)\n"
            "3) Strengths (use rubric strengths and/or 'You excelled at')\n"
            "4) Areas for improvement (use rubric improvement items and/or 'work on')\n"
            "5) Actionable suggestions (3–6 bullets, practical and measurable)\n"
            "6) To challenge yourself (1–3 bullets)\n"
            "7) Alignment to project purpose (1 short paragraph: how the feedback supports the purpose)\n\n"
            "Rules:\n"
            "- Use ONLY what is in the provided notes. If something is not observed, say 'Not observed' or omit.\n"
            "- Keep tone encouraging and professional.\n"
            "- Avoid long essays; be structured.\n"
            "- If evaluator notes include rubric ratings, explicitly reference the relevant skill areas.\n"
        ),
        expected_output="A complete evaluation draft in Markdown.",
        agent=draft_agent,
        context=[context],
    )

    check_task = Task(
        description=(
            "Review the draft and return:\n"
            "A) A short list of issues (if any): hallucinations, vagueness, missing alignment.\n"
            "B) Concrete improvements to make the draft stronger.\n"
            "C) A one-line verdict: 'Aligned' or 'Needs fixes'.\n\n"
            "Be strict: do not allow invented observations."
        ),
        expected_output="Quality check notes + verdict.",
        agent=checker_agent,
        context=[draft_task],
    )

    final_task = Task(
        description=(
            "Revise the evaluation draft using the checker feedback.\n"
            "Output ONLY the final improved Markdown evaluation draft.\n"
            "Ensure:\n"
            "- Strengths reflect 4–5 rubric items and positive notes.\n"
            "- Improvements reflect 1–3 rubric items and 'work on'.\n"
            "- Suggestions are measurable (e.g., 'Add 2 planned pauses' not 'be better').\n"
            "- No invented details.\n"
        ),
        expected_output="Final polished Markdown evaluation draft.",
        agent=draft_agent,
        context=[draft_task, check_task],
    )

    crew = Crew(
        agents=[draft_agent, checker_agent],
        tasks=[draft_task, check_task, final_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    demo = run_crewai_eval(
        notes=(
            "Speaker: Alex\nEvaluator: Oscar\nDate: 2026-01-17\n"
            "Strengths: - Clarity (4/5)\nImprovements: - Vocal Variety (3/5)\n"
            "You excelled at: strong structure\nWork on: more pauses\nChallenge: add 1 audience question"
        ),
        pathway="Presentation Mastery",
        level="Level 1",
        project="Ice Breaker",
        level_focus="Mastering fundamentals",
        purpose="Introduce yourself and practice organising a basic public speech.",
        speech_len="4–6 minutes",
    )
    print(demo)


