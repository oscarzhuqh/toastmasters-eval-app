# crewai_eval.py
from __future__ import annotations

import os
from typing import Optional

from crewai import Agent, Task, Crew, Process


def _get_secret(name: str) -> Optional[str]:
    """
    Read Streamlit secrets if available, else None.
    """
    try:
        import streamlit as st  # type: ignore

        if hasattr(st, "secrets") and name in st.secrets:
            val = str(st.secrets[name]).strip()
            return val or None
    except Exception:
        pass
    return None


def _get_api_key() -> Optional[str]:
    # 1) Streamlit secrets
    key = _get_secret("OPENAI_API_KEY")
    if key:
        return key

    # 2) Environment variable
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key or None


def _get_model() -> str:
    """
    Replace:
      model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    With:
      model = os.getenv("OPENAI_MODEL", "").strip()
      (then secrets override)
      (then fallback)
    """
    model = os.getenv("OPENAI_MODEL", "").strip()

    # Streamlit secrets can override model too
    secret_model = _get_secret("OPENAI_MODEL")
    if secret_model:
        model = secret_model.strip()

    return model or "gpt-4o-mini"


def _make_llm():
    """
    Creates an LLM object compatible with CrewAI.
    - If CrewAI exposes `crewai.LLM`, use it.
    - Otherwise, rely on env vars (many CrewAI setups read from env).
    """
    api_key = _get_api_key()
    model = _get_model()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Add it to Streamlit Secrets (OPENAI_API_KEY) "
            "or set it as an environment variable."
        )

    # Newer CrewAI versions
    try:
        from crewai import LLM  # type: ignore

        return LLM(model=model, api_key=api_key)
    except Exception:
        # Fallback: set env vars and let CrewAI/OpenAI stack pick it up
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
    Returns a structured Toa


