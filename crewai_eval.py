"""CrewAI evaluation generator for Toastmasters Evaluation Assistant (T.E.A.).

Submission version features:
- Robust generation: uses CrewAI when available; falls back to a single LLM call.
- Meeting-ready structure: Markdown with clear headings that map to the export form layout.
- Anti-hallucination Purpose Alignment: evidence-bound claims + "Insufficient evidence..." fallback.
- Includes "Rubric Snapshot" so rubric ratings/comments appear in exports.

App expects:
    from crewai_eval import run_crewai_eval
"""

from __future__ import annotations

import os
import re
from typing import Optional


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
                    {"role": "system", "content": "You are a Toastmasters speech evaluation assistant."},
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
    """Extract a short 1–2 sentence summary from the Purpose Alignment section (if present)."""
    md = (md_text or "").strip()
    if not md:
        return ""

    m = re.search(r"^#{1,3}\s+Purpose\s+Alignment.*$", md, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""

    section = md[m.end():]
    section = re.split(r"^#{1,3}\s+", section, maxsplit=1, flags=re.MULTILINE)[0].strip()
    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]

    out = []
    for ln in lines:
        if re.match(r"^-\s*\[(x| )\]\s+", ln, flags=re.IGNORECASE):
            break
        if ln.lower().startswith("evidence:"):
            continue
        if ln.startswith("-") and not ln.lower().startswith("- alignment claim"):
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
    """Generate an evaluation draft (Markdown). Extra kwargs are accepted for forward compatibility."""
    api_key = _get_setting("OPENAI_API_KEY", "")
    model = _get_setting("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return (
            "❌ Missing OPENAI_API_KEY.\n\n"
            "Add it in Streamlit secrets (recommended) or environment variables.\n"
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
suitable for a real Toastmasters club meeting.

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

Evaluation criteria reference (rubric meaning):
{criteria_text.strip() or "(No criteria text provided)"}

Evaluator input (rubric summary + comments + general notes):
{notes}

Write the output as a structured evaluation draft in plain English.

Required structure (use Markdown headings exactly):

## Opening
Write 2–3 sentences (~40–70 words). The opening should:
- Thank the speaker and mention the speech title
- Clearly link back to the project purpose
- Use a warm, encouraging Toastmasters tone

## Strengths
Write 3–5 bullet points. Each bullet should be ~20–30 words and should:
- State one clear strength
- Include a brief explanation or example from the notes
- Link back to evaluation criteria where possible

## Rubric Snapshot
- Include a compact list of the rubric items as provided (criterion, rating/5, and the evaluator's short comment if any).
- Do NOT invent comments. If a comment is missing, write "(no comment)".

## Recommendations
Write 3–5 bullet points (~18–28 words each). Each bullet should:
- State one improvement area
- Include a brief explanation or example from the notes
- Link back to evaluation criteria where possible

## One Challenge
Write 1–2 sentences (~25–45 words). Make it very actionable and phrased as the next step.

## Purpose Alignment (Evidence-bound, anti-hallucination)
Write an evidence-based alignment summary. You may ONLY make alignment claims that are directly supported by:
(a) the stated Project Purpose
(b) the stated Level Focus
(c) the evaluator’s rubric ratings/comments
(d) the evaluator’s general comments

Do not restate the project purpose verbatim unless it is used as Evidence.

For each claim, you MUST include an Evidence line quoting or paraphrasing from the provided notes.
If there is insufficient evidence, write: "Insufficient evidence in the provided notes to confirm this."

Format exactly:
### Evidence-backed alignment
- Alignment claim: <short claim>
  Evidence: <quote/paraphrase from Purpose/Level Focus/Rubric/Comments OR the insufficient-evidence sentence>

(Write 2–3 claim/evidence pairs.)

### Checklist (auto)
- [ ] Purpose clearly addressed
- [ ] Level focus demonstrated
- [ ] Feedback linked to evaluation criteria
- [ ] Balanced commendations + improvements
- [ ] Actionable next step provided

### Why (2–3 bullets)
- <bullet explaining which evidence supports checked items and what is missing if unchecked>

Rules:
- Reuse rubric comments explicitly: reference the evaluator's rubric notes and ratings (paraphrase or short quotes) instead of generic statements.
- Be specific, but do not invent details.
- If details are missing, use "Based on the notes provided..." and keep it general.
- Tone: supportive, respectful, Toastmasters-appropriate.
- Output Markdown only.
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
            goal="Ensure the draft follows the required headings and the Purpose Alignment section is evidence-bound.",
            backstory="You ensure evaluations are objective, rubric-aligned, and project-relevant with audit-ready evidence.",
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
                "Review the evaluation draft. Ensure headings match exactly: "
                "Opening, Strengths, Rubric Snapshot, Recommendations, One Challenge, Purpose Alignment. "
                "Ensure Purpose Alignment uses the Evidence-backed format with Evidence lines. "
                "Repair any missing checklist items. Keep Markdown only."
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
