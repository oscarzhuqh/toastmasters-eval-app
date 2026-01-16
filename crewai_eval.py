# crewai_eval.py
import os

from crewai import Agent, Task, Crew, Process


def _get_secret(name):
    try:
        import streamlit as st  # type: ignore

        if hasattr(st, "secrets") and name in st.secrets:
            val = str(st.secrets[name]).strip()
            return val or None
    except Exception:
        return None
    return None


def _get_api_key():
    key = _get_secret("OPENAI_API_KEY")
    if key:
        return key
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key or None


def _get_model():
    model = os.getenv("OPENAI_MODEL", "").strip()

    secret_model = _get_secret("OPENAI_MODEL")
    if secret_model:
        model = secret_model.strip()

    return model or "gpt-4o-mini"


def _make_llm():
    api_key = _get_api_key()
    model = _get_model()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Add it to Streamlit Secrets (OPENAI_API_KEY) "
            "or set it as an environment variable."
        )

    # Newer CrewAI versions may support this
    try:
        from crewai import LLM  # type: ignore

        return LLM(model=model, api_key=api_key)
    except Exception:
        # Fallback: rely on env vars
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_MODEL"] = model
        return None


def run_crewai_eval(notes, pathway, level, project, level_focus, purpose, speech_len):
    llm = _make_llm()

    context_block = (
        "Toastmasters context (from knowledge base):\n"
        f"- Pathway: {pathway}\n"
        f"- Level: {level}\n"
        f"- Project: {project}\n"
        f"- Level focus: {level_focus}\n"
        f"- Purpose: {purpose}\n"
        f"- Speech length: {speech_len}\n\n"
        "Evaluator notes (ONLY source of truth — do not invent anything):\n"
        f"{notes}"
    )

    draft_agent = Agent(
        role="Toastmasters Evaluation Drafter",
        goal="Draft a clear, supportive, specific evaluation aligned to the project purpose and level focus.",
        backstory=(
            "You are an experienced Toastmasters evaluator. You write constructive feedback that is "
            "actionable, kind, and aligned to evaluation criteria. You never invent observations."
        ),
        allow_delegation=False,
        verbose=False,
        llm=llm,
    )

    draft_task = Task(
        description=(
            "Using the context below, write a Toastmasters evaluation draft in MARKDOWN.\n\n"
            "Output structure (use headings):\n"
            "## Header\n"
            "- Speaker:\n"
            "- Evaluator:\n"
            "- Date:\n\n"
            "## Overall Summary (2–4 sentences)\n\n"
            "## Strengths\n"
            "- Use rubric items rated 4–5 and/or 'You excelled at'.\n"
            "- Be specific and evidence-based.\n\n"
            "## Areas for Improvement\n"
            "- Use rubric items rated 1–3 and/or 'You may want to work on'.\n"
            "- Be supportive and clear.\n\n"
            "## Actionable Suggestions (3–6 bullets)\n"
            "- Measurable, practical next steps.\n\n"
            "## To Challenge Yourself (1–3 bullets)\n\n"
            "## Alignment to Project Purpose (1 short paragraph)\n"
            "- Explain how the feedback helps the speaker meet the project purpose.\n\n"
            "Rules:\n"
            "- DO NOT add any details not present in the evaluator notes.\n"
            "- If something is not observed, omit it or say 'Not observed'.\n"
            "- Keep tone encouraging and professional.\n\n"
            "CONTEXT:\n"
            f"{context_block}"
        ),
        expected_output="A complete evaluation draft in Markdown with the exact structure requested.",
        agent=draft_agent,
    )

    crew = Crew(
        agents=[draft_agent],
        tasks=[draft_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return str(result)

