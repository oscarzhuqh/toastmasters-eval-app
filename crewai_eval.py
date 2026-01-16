# crewai_eval.py
from __future__ import annotations

import os
from typing import Optional

# CrewAI imports (works for most CrewAI versions)
from crewai import Agent, Task, Crew, Process


def _get_api_key() -> Optional[str]:
    """
    Tries (in order):
      1) Streamlit secrets (if running inside Streamlit Cloud)
      2) Environment variable OPENAI_API_KEY
    """
    # Streamlit secrets (optional)
    try:
        import streamlit as st  # type: ignore
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            return str(st.secrets["OPENAI_API_KEY"]).strip()
    except Exception:
        pass

    # Env var
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key or None


def _make_llm():
    """
    Creates an LLM object compatible with CrewAI.

    Works across common setups:
      - If your CrewAI supports `crewai.LLM`, use it.
      - Otherwise, let CrewAI use the provider/model via env vars.

    Recommended env vars:
      OPENAI_API_KEY
      OPENAI_MODEL (optional, default below)
    """
    api_key = _get_api_key()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    # Newer CrewAI versions expose an LLM helper
    try:
        from crewai import LLM  # type: ignore

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found. Set it in Streamlit Secrets or environment variables."
            )

        return LLM(
            model=model,
            api_key=api_key,
        )
    except Exception:
        # Fallback: return a dict-like config that many setups accept, or None.
        # CrewAI may read OPENAI_API_KEY directly from env, so this can still work.
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found. Set it in Streamlit Secrets or environment variables."
            )
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
    Uses evaluator notes + KB fields (purpose, level_focus, etc.) as context.

    Your Streamlit app should pass:
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
            "Draft

