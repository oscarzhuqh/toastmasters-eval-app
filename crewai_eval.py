import os

# CrewAI is optional. If not installed, we fall back to a simple OpenAI call.


def _get_setting(name: str, default: str = "") -> str:
    """Get from env first, then Streamlit secrets if available."""
    val = os.getenv(name, default)
    try:
        import streamlit as st  # type: ignore

        if hasattr(st, "secrets") and name in st.secrets:
            val = str(st.secrets[name])
    except Exception:
        pass
    return (val or "").strip()


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
    total_score=None,
    score_label: str = "",
) -> str:
    """Generate a structured Toastmasters evaluation draft (markdown)."""

    api_key = _get_setting("OPENAI_API_KEY")
    model = _get_setting("OPENAI_MODEL", "gpt-4o-mini")

    # Build a single, strong context block.
    score_line = ""
    if total_score is not None and str(total_score).strip() != "":
        score_line = f"Overall rubric score: {total_score}/40"
        if score_label:
            score_line += f" ({score_label})"

    context = f"""
You are a Toastmasters evaluation draft assistant.

Write a helpful, encouraging evaluation draft that is:
- aligned to the selected Pathways project (purpose + level focus)
- grounded in the rubric ratings + comments provided
- structured like a real Toastmasters evaluation (strengths, improvements, challenge, close)

Project context
- Pathway: {pathway}
- Level: {level}
- Project: {project}
- Purpose: {purpose}
- Speech length: {speech_len}
- Level focus: {level_focus}
{score_line}

Rubric criteria reference (for evaluator understanding):
{criteria_text}

Evaluator inputs (rubric ratings, comments, and notes):
{notes}

Requirements
- Output MUST be markdown.
- Use clear headings.
- Keep it printable (no huge tables).
- Do not invent facts that aren't in the notes.
""".strip()

    # --- Try CrewAI first ---
    try:
        from crewai import Agent, Task, Crew, Process  # type: ignore

        # CrewAI usually needs a working LLM provider configured via env.
        # We'll still run it; if the user hasn't configured, it will throw and we fall back.
        evaluator = Agent(
            role="Toastmasters Speech Evaluator",
            goal="Create an accurate, supportive, project-aligned evaluation draft",
            backstory=(
                "You are an experienced Toastmasters evaluator. You give specific, actionable feedback "
                "and connect comments to the speech project purpose and skills."
            ),
            verbose=False,
        )

        task = Task(
            description=context,
            expected_output=(
                "A markdown evaluation draft with sections: Overview, Strengths, Areas to Improve, "
                "One Challenge, Suggested Next Steps, and a short Closing."
            ),
            agent=evaluator,
        )

        crew = Crew(
            agents=[evaluator],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        result = crew.kickoff()
        return str(result).strip() or "(No output returned by CrewAI.)"

    except Exception:
        # --- Fallback: direct OpenAI call (if key exists) ---
        if not api_key:
            return (
                "CrewAI/OpenAI is not configured yet.\n\n"
                "Add `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`) to Streamlit Secrets or environment variables, "
                "then try again.\n\n"
                "For now, your notes were captured successfully, but no AI draft can be generated without a key."
            )

        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You generate Toastmasters evaluation drafts in markdown."},
                    {"role": "user", "content": context},
                ],
                temperature=0.5,
            )
            return (resp.choices[0].message.content or "").strip() or "(No output returned.)"
        except Exception as e:
            return f"Failed to generate draft. Error: {type(e).__name__}: {e}"


# ---------------- Purpose Alignment Summary (Lightweight Evidence Helper) ----------------
def purpose_alignment_summary(
    purpose: str,
    evaluator_notes: str,
    draft_md: str,
    speech_title: str = "",
    model: str | None = None,
) -> str:
    """Return a short, report-friendly summary indicating whether the speech met the selected project purpose.
    Uses the configured LLM (same env/secrets as generation). If LLM is unavailable, returns a heuristic message.
    """

    purpose = (purpose or "").strip()
    evaluator_notes = (evaluator_notes or "").strip()
    draft_md = (draft_md or "").strip()

    if not purpose:
        return "**Purpose alignment:** Unable to assess (missing project purpose)."

    if not evaluator_notes and not draft_md:
        return (
            "**Purpose alignment (quick check):** Unable to assess confidently because evaluator notes/draft are empty.\n\n"
            f"**Target purpose:** {purpose}"
        )

    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY")
    if not api_key:
        return (
            "**Purpose alignment (quick check):** LLM is not configured (missing API key), so no automated check was run.\n\n"
            f"**Target purpose:** {purpose}\n"
            "**Tip:** Add a few bullets in Evaluator Notes describing what the speaker did relative to the purpose."
        )

    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)

        title_line = f"Speech title: {speech_title}\n" if speech_title else ""

        prompt = (
            "You are checking whether a Toastmasters speech met its project purpose.\n"
            "Return a SHORT report-friendly result with:\n"
            "1) Verdict: Met / Partially Met / Not Met (one of these only)\n"
            "2) 2 evidence bullets grounded ONLY in evaluator notes (prefer notes) or the draft text if notes are insufficient\n"
            "3) 1 improvement bullet that ties back to the purpose\n\n"
            "Target purpose:\n" + purpose + "\n\n" +
            title_line +
            "Evaluator notes:\n" + evaluator_notes + "\n\n" +
            "Draft (for reference):\n" + draft_md
        )

        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Be strict about grounding. Do not invent facts."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise ValueError("Empty response")

        return "**Purpose alignment (quick check)**\n\n" + content

    except Exception as e:
        return (
            "**Purpose alignment (quick check):** Automated check failed.\n\n"
            f"Error: `{type(e).__name__}: {e}`\n\n"
            f"**Target purpose:** {purpose}"
        )
