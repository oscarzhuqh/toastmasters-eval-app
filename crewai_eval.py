# crewai_eval.py
import os
from typing import Any, Dict, Optional, Tuple

from crewai import Agent, Task, Crew, Process


# -------------------- SECRETS / ENV --------------------
def _get_secret(name: str) -> Optional[str]:
    try:
        import streamlit as st  # type: ignore

        if hasattr(st, "secrets") and name in st.secrets:
            val = str(st.secrets[name]).strip()
            return val or None
    except Exception:
        return None
    return None


def _get_api_key() -> Optional[str]:
    # Streamlit secrets first, then env
    key = _get_secret("OPENAI_API_KEY")
    if key:
        return key
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key or None


def _get_model() -> str:
    # Env first
    model = os.getenv("OPENAI_MODEL", "").strip()

    # Streamlit secrets can override model
    secret_model = _get_secret("OPENAI_MODEL")
    if secret_model:
        model = secret_model.strip()

    return model or "gpt-4o-mini"


def _make_llm():
    """
    Try CrewAI's LLM wrapper (newer versions). If unavailable, fallback to env vars.
    """
    api_key = _get_api_key()
    model = _get_model()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found.\n\n"
            "✅ Streamlit Cloud: App → Settings → Secrets → add:\n"
            "OPENAI_API_KEY = \"your_key\"\n\n"
            "OR set it as an environment variable OPENAI_API_KEY."
        )

    try:
        from crewai import LLM  # type: ignore

        return LLM(model=model, api_key=api_key)
    except Exception:
        # Fallback: rely on env vars used by underlying provider
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_MODEL"] = model
        return None


# -------------------- HELPERS --------------------
def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    return str(x).strip()


def _normalize_rubric(
    rubric: Optional[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], int]:
    """
    Accepts multiple shapes:
    - {"Clarity": 3, "Vocal Variety": 4}
    - {"Clarity": {"rating": 3, "comment": "..."}, ...}
    - {"Clarity": {"score": 3, "notes": "..."}}
    Returns normalized:
    - {"Clarity": {"rating": 3, "comment": "..."}}
    And total score.
    """
    norm: Dict[str, Dict[str, Any]] = {}
    total = 0

    if not rubric:
        return norm, 0

    for k, v in rubric.items():
        criterion = _safe_str(k)
        rating = None
        comment = ""

        if isinstance(v, (int, float, str)):
            try:
                rating = int(v)
            except Exception:
                rating = None
        elif isinstance(v, dict):
            # common keys
            for rk in ["rating", "score", "value"]:
                if rk in v:
                    try:
                        rating = int(v[rk])
                        break
                    except Exception:
                        rating = None
            for ck in ["comment", "notes", "remark"]:
                if ck in v and v[ck] is not None:
                    comment = _safe_str(v[ck])
                    break
        else:
            # unknown object
            comment = _safe_str(v)

        if rating is not None:
            rating = max(1, min(5, rating))
            total += rating

        norm[criterion] = {"rating": rating, "comment": comment}

    return norm, total


def _score_band(total: int) -> str:
    # For 8 criteria (8–40). If you later add/remove criteria, you can adjust bands.
    if total >= 32:
        return "Outstanding (32–40)"
    if total >= 24:
        return "Exceed Expectation of Speech Project (24–31)"
    if total >= 16:
        return "Meets Minimum Expectation of Speech Project (16–23)"
    return "Needs Improvement (8–15)"


def _format_rubric_lines(rubric_norm: Dict[str, Dict[str, Any]]) -> str:
    if not rubric_norm:
        return "- (No rubric ratings provided)"
    lines = []
    for c, obj in rubric_norm.items():
        r = obj.get("rating", None)
        com = _safe_str(obj.get("comment", ""))
        r_txt = str(r) if r is not None else "N/A"
        if com:
            lines.append(f"- {c}: {r_txt}/5 — {com}")
        else:
            lines.append(f"- {c}: {r_txt}/5")
    return "\n".join(lines)


def _derive_strengths_improvements(rubric_norm: Dict[str, Dict[str, Any]]):
    strengths = []
    improvements = []
    for c, obj in rubric_norm.items():
        r = obj.get("rating", None)
        if r is None:
            continue
        if r >= 4:
            strengths.append(f"{c} ({r}/5)")
        else:
            improvements.append(f"{c} ({r}/5)")
    return strengths, improvements


# -------------------- MAIN ENTRY --------------------
def run_crewai_eval(
    notes,
    pathway,
    level,
    project,
    level_focus,
    purpose,
    speech_len,
    # Newer optional fields (safe to ignore if your app doesn't pass them yet)
    speaker_name: Optional[str] = None,
    evaluator_name: Optional[str] = None,
    meeting_date: Optional[str] = None,
    speech_title: Optional[str] = None,
    rubric: Optional[Dict[str, Any]] = None,
    total_score: Optional[int] = None,
    strengths: Optional[list] = None,
    improvements: Optional[list] = None,
) -> str:
    """
    Generates a structured evaluation draft using CrewAI.

    Backward compatible:
      run_crewai_eval(notes, pathway, level, project, level_focus, purpose, speech_len)

    Recommended (new):
      run_crewai_eval(..., speaker_name=..., evaluator_name=..., meeting_date=..., speech_title=...,
                      rubric={...}, total_score=..., strengths=[...], improvements=[...])
    """
    llm = _make_llm()

    # Normalize rubric if provided
    rubric_norm, computed_total = _normalize_rubric(rubric)

    # Total score precedence: explicit total_score > computed rubric total > 0
    final_total = total_score if isinstance(total_score, int) else computed_total
    band = _score_band(final_total) if final_total else "N/A"

    # Derive strengths/improvements if not provided
    if strengths is None or improvements is None:
        s2, i2 = _derive_strengths_improvements(rubric_norm)
        strengths = strengths or s2
        improvements = improvements or i2

    strengths_txt = "\n".join([f"- {x}" for x in strengths]) if strengths else "- (None selected)"
    improvements_txt = "\n".join([f"- {x}" for x in improvements]) if improvements else "- (None selected)"

    # Notes can be dict or string
    if isinstance(notes, dict):
        notes_str = "\n".join([f"- {k}: {notes.get(k)}" for k in notes.keys()])
    else:
        notes_str = _safe_str(notes)

    # Compact “criteria meaning” in our own words (not verbatim)
    criteria_guide = (
        "Rubric meaning (general guide):\n"
        "- 5: Exemplary / model performance\n"
        "- 4: Strong / above average\n"
        "- 3: Acceptable / meets baseline\n"
        "- 2: Developing / needs practice\n"
        "- 1: Needs significant improvement\n"
    )

    context_block = (
        "Toastmasters project context (from knowledge base):\n"
        f"- Pathway: {pathway}\n"
        f"- Level: {level}\n"
        f"- Project: {project}\n"
        f"- Level focus: {level_focus}\n"
        f"- Purpose: {purpose}\n"
        f"- Speech length: {speech_len}\n\n"
        "Meeting details:\n"
        f"- Speaker: {_safe_str(speaker_name) or '(not provided)'}\n"
        f"- Evaluator: {_safe_str(evaluator_name) or '(not provided)'}\n"
        f"- Date: {_safe_str(meeting_date) or '(not provided)'}\n"
        f"- Speech title: {_safe_str(speech_title) or '(not provided)'}\n\n"
        "Rubric summary:\n"
        f"- Total score: {final_total if final_total else 'N/A'}\n"
        f"- Band: {band}\n"
        f"{criteria_guide}\n"
        "Rubric ratings + comments:\n"
        f"{_format_rubric_lines(rubric_norm)}\n\n"
        "Auto-grouping rule:\n"
        "- Ratings 4–5 → Strengths\n"
        "- Ratings 1–3 → Areas for improvement\n\n"
        "Derived groups:\n"
        "Strengths:\n"
        f"{strengths_txt}\n"
        "Areas for improvement:\n"
        f"{improvements_txt}\n\n"
        "Evaluator rough notes (ONLY source of truth — do not invent):\n"
        f"{notes_str if notes_str else '(no notes provided)'}\n"
    )

    draft_agent = Agent(
        role="Toastmasters Evaluation Drafter",
        goal="Draft a clear, supportive, specific evaluation aligned to the project purpose and level focus, using rubric ratings and evaluator notes.",
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
            "Write a Toastmasters evaluation draft in MARKDOWN.\n\n"
            "Hard rules:\n"
            "- DO NOT invent anything not stated in rubric comments or evaluator notes.\n"
            "- If something is not observed, omit it or say 'Not observed'.\n"
            "- Keep tone encouraging and professional.\n\n"
            "Output structure (use these headings):\n"
            "## Header\n"
            "- Speaker: <name>\n"
            "- Evaluator: <name>\n"
            "- Date: <date>\n"
            "- Speech title: <title>\n"
            "- Project: <pathway / level / project>\n"
            "- Total score + band: <e.g., 27/40 — Exceed Expectation>\n\n"
            "## Overall Summary (2–4 sentences)\n"
            "- Summarise overall performance and tie back to project purpose.\n\n"
            "## Strengths (based on ratings 4–5)\n"
            "- Use the rubric areas rated 4–5.\n"
            "- Include 1–2 specific evidence points from comments/notes.\n\n"
            "## Areas for Improvement (based on ratings 1–3)\n"
            "- Use the rubric areas rated 1–3.\n"
            "- Keep supportive; avoid harsh wording.\n\n"
            "## Actionable Suggestions (3–6 bullets)\n"
            "- Practical, measurable next steps.\n\n"
            "## To Challenge Yourself (1–3 bullets)\n"
            "- A stretch goal aligned to the project.\n\n"
            "## Alignment to Project Purpose (1 short paragraph)\n"
            "- Explain how the feedback helps meet the project purpose.\n\n"
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

