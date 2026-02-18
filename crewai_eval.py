"""CrewAI evaluation generator for Toastmasters Evaluation Assistant (T.E.A.).

This module generates a Toastmasters-style evaluation draft (Markdown) from:
- Pathways project context (purpose, level focus, speech length)
- Evaluator inputs (rubric ratings/comments + general notes)

Guardrail focus (Responsible AI):
- Evidence-bound Purpose Alignment: alignment claims and checklist indicators must be supported by
  explicit evidence from evaluator inputs and/or provided project metadata.
- Placeholder inputs (e.g., '-', 'n/a') are treated as missing evidence.
- If evaluator evidence is insufficient, alignment is conservatively withheld and indicators are
  auto-unchecked (meeting-safe behaviour).

App expects:
    from crewai_eval import run_crewai_eval, purpose_alignment_summary
"""

from __future__ import annotations

import os
import re
from typing import Optional, Dict, Tuple


# -----------------------------
# Settings / LLM fallback
# -----------------------------
def _get_setting(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first (if available), else environment variables."""
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
            resp = client.responses.create(model=model, input=prompt)
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


# -----------------------------
# Evidence / guardrail helpers
# -----------------------------
_PLACEHOLDERS = {
    "-", "—", "–",
    "n/a", "na", "nil", "none", "null",
    "not sure", "unsure", "no comment", "no comments",
    "tbd",
}


def _norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _is_placeholder_line(line: str) -> bool:
    t = _norm_text(line)
    if not t:
        return True
    if t in _PLACEHOLDERS:
        return True
    # Lines that are only punctuation / dashes
    if re.fullmatch(r"[-–—\s]+", line.strip()):
        return True
    return False


def _has_substantive_evaluator_evidence(notes: str) -> bool:
    """Returns True if evaluator notes contain meaningful text beyond placeholders."""
    if not (notes or "").strip():
        return False

    # Drop common boilerplate and placeholder-only lines
    lines = [ln.strip() for ln in (notes or "").splitlines()]
    kept: list[str] = []
    for ln in lines:
        if not ln:
            continue
        if _is_placeholder_line(ln):
            continue
        kept.append(ln)

    if not kept:
        return False

    # Require at least a few alphabetic tokens (prevents '...' from counting)
    joined = " ".join(kept)
    tokens = re.findall(r"[A-Za-z]{3,}", joined)
    return len(tokens) >= 3


def _has_rubric_comment_evidence(notes: str) -> bool:
    """Heuristic: detects at least one rubric line with a non-trivial comment.

    Accepts formats like:
      - Clarity: 4/5 - Strong clarity throughout...
      - Vocal Variety: 3/5 - (no comment)   -> treated as missing
    """
    txt = notes or ""
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        # Common rubric snapshot line pattern
        m = re.match(r"^[-•\*]?\s*([A-Za-z][A-Za-z\s/]+):\s*\d\s*/\s*5\s*-\s*(.+)$", ln)
        if not m:
            continue
        comment = m.group(2).strip()
        if _is_placeholder_line(comment):
            continue
        # Avoid '(no comment)' / similar
        if _norm_text(comment) in {"(no comment)", "no comment", "(none)", "none"}:
            continue
        # Require some meaningful length
        if len(re.findall(r"[A-Za-z]{3,}", comment)) >= 3:
            return True
    return False


def _ensure_purpose_alignment_section(md: str) -> str:
    md = (md or "").strip()
    if not md:
        return ""
    if re.search(r"^##\s+Purpose\s+Alignment\s*$", md, flags=re.IGNORECASE | re.MULTILINE):
        return md
    # Append a minimal section if missing
    return md + "\n\n## Purpose Alignment\n- [ ] Purpose clearly addressed\n- [ ] Level focus demonstrated\n- [ ] Feedback linked to evaluation criteria\n- [ ] Balanced commendations + improvements\n- [ ] Actionable next step provided\n"


def _set_checkbox(md: str, label: str, checked: bool) -> str:
    """Set a single markdown task list item in the Purpose Alignment section."""
    md = _ensure_purpose_alignment_section(md)

    # Replace only inside Purpose Alignment section
    parts = re.split(r"(^##\s+Purpose\s+Alignment\s*$)", md, flags=re.IGNORECASE | re.MULTILINE)
    if len(parts) < 3:
        return md

    before = "".join(parts[:2])
    rest = "".join(parts[2:])

    # isolate section body
    sec_body = re.split(r"^##\s+", rest, maxsplit=1, flags=re.MULTILINE)[0]
    after = rest[len(sec_body):]

    # pattern for the specific label
    pattern = re.compile(rf"(^\s*[-•]\s*\[(?:x| )\]\s*{re.escape(label)}\s*$)", re.IGNORECASE | re.MULTILINE)
    repl_line = f"- [{'x' if checked else ' '}] {label}"
    if pattern.search(sec_body):
        sec_body = pattern.sub(repl_line, sec_body)
    else:
        # If missing, append it near top
        sec_body = sec_body.rstrip() + "\n" + repl_line + "\n"

    return before + sec_body + after


def _replace_purpose_alignment_with_withheld_block(md: str) -> str:
    """Overwrite Purpose Alignment section with a conservative withheld block."""
    md = (md or "").strip()
    if not md:
        return md

    withheld = """## Purpose Alignment
Alignment was **withheld** due to insufficient evaluator evidence (e.g., placeholder-only notes or missing rubric comments). This prevents unsupported alignment claims.

- [ ] Purpose clearly addressed
- [ ] Level focus demonstrated
- [ ] Feedback linked to evaluation criteria
- [ ] Balanced commendations + improvements
- [ ] Actionable next step provided

- Guardrail: Purpose alignment indicators require *specific* evaluator observations or criterion comments.
- Guardrail: When evidence is missing, indicators are conservatively left unchecked for human review.
""".rstrip()

    # If section exists, replace it; else append.
    m = re.search(r"^##\s+Purpose\s+Alignment\s*$", md, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return md + "\n\n" + withheld + "\n"

    start = m.start()
    # find end of section (next '## ' heading or end)
    after_start = md[m.end():]
    nxt = re.search(r"^##\s+", after_start, flags=re.MULTILINE)
    end = m.end() + (nxt.start() if nxt else len(after_start))
    return (md[:start].rstrip() + "\n\n" + withheld + "\n\n" + md[end:].lstrip()).strip()


# -----------------------------
# Public helpers (reports)
# -----------------------------
def purpose_alignment_summary(md_text: str) -> str:
    """Return a short 1–2 sentence summary if a Purpose Alignment section exists."""
    md = (md_text or "").strip()
    if not md:
        return ""

    m = re.search(r"^##\s+Purpose\s+Alignment\s*$", md, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""

    section = md[m.end():]
    section = re.split(r"^##\s+", section, maxsplit=1, flags=re.MULTILINE)[0].strip()
    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]

    out: list[str] = []
    for ln in lines:
        if re.match(r"^[-•]\s*\[(x| )\]\s+", ln, flags=re.IGNORECASE):
            break
        if ln.startswith("-"):
            continue
        out.append(ln)
        if len(out) >= 2:
            break
    return " ".join(out).strip()


# -----------------------------
# Main entrypoint
# -----------------------------
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
    """Generate an editable evaluation draft (Markdown)."""

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

    # Guardrail pre-check: if evaluator evidence is missing, we still generate the draft,
    # but we will *withhold* alignment indicators in post-processing.
    has_eval_evidence = _has_substantive_evaluator_evidence(notes)
    has_rubric_comment = _has_rubric_comment_evidence(notes)

    purpose_alignment_guardrail_block = """## Purpose Alignment (Evidence-Bound)
You MUST follow these rules:
1) Only make alignment claims if you can quote or paraphrase *explicit evidence* from:
   - evaluator notes / rubric comments, OR
   - the provided Project Purpose / Level Focus text (metadata).
2) If evaluator notes are placeholders (e.g., '-', 'n/a') or contain no specific observations,
   then you MUST conservatively mark indicators as unsupported.
3) For the checklist below:
   - "Feedback linked to evaluation criteria" can ONLY be checked if there is at least one
     non-trivial per-criterion evaluator comment (not placeholders).
4) If evidence is insufficient, write: "Alignment withheld due to insufficient evidence."
   and leave the relevant boxes unchecked.
""".strip()

    prompt = f"""
You are the Toastmasters Evaluation Assistant (T.E.A.).

Goal:
Turn the evaluator's rubric ratings + notes into a clear, kind, project-aligned evaluation draft
suitable for a real Toastmasters club meeting.

Meeting details:
- Speaker: {speaker_name or "(not provided)"}
- Evaluator: {evaluator_name or "(not provided)"}
- Date: {meeting_date or "(not provided)"}
- Speech Title: {speech_title or "(not provided)"}
{score_line}

Pathways context (metadata you may quote as evidence):
- Pathway: {pathway}
- Level: {level}
- Project: {project}
- Project Purpose: {purpose}
- Level Focus: {level_focus}
- Target speech length: {speech_len}

Evaluation criteria reference:
{criteria_text.strip() or "(No criteria text provided)"}

Evaluator input (rubric summary + comments + general notes):
{notes}

Write the output as a structured evaluation draft in Markdown.

Required headings (use EXACTLY these Markdown headings):
## Opening
## Strengths
## Recommendations
## One Challenge
{purpose_alignment_guardrail_block}
(Then include the checklist below)

Checklist (Markdown task list):
- [ ] Purpose clearly addressed
- [ ] Level focus demonstrated
- [ ] Feedback linked to evaluation criteria
- [ ] Balanced commendations + improvements
- [ ] Actionable next step provided

Rules:
- Do NOT invent details.
- If details are missing, say "Based on the notes provided..." and keep it general.
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
            goal="Write a clear, supportive Toastmasters evaluation draft aligned to Pathways goals.",
            backstory="You are a seasoned Toastmasters evaluator who focuses on actionable feedback.",
            llm=llm,
            verbose=False,
        )

        alignment = Agent(
            role="Alignment Checker",
            goal="Ensure the draft is evidence-bound and conservatively handles missing evaluator evidence.",
            backstory="You enforce guardrails: no unsupported claims; indicators must be evidence-backed.",
            llm=llm,
            verbose=False,
        )

        draft_task = Task(
            description=prompt,
            expected_output="A complete markdown evaluation draft following the required headings and rules.",
            agent=evaluator,
        )

        check_task = Task(
            description=(
                "Review the evaluation draft and ensure headings match exactly: "
                "Opening, Strengths, Recommendations, One Challenge, Purpose Alignment. "
                "Ensure the checklist exists and follows the evidence-bound guardrails."
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
            md_out = result.strip()
        else:
            md_out = ""
            for attr in ("raw", "output", "final_output"):
                if hasattr(result, attr):
                    value = getattr(result, attr)
                    if value:
                        md_out = str(value).strip()
                        break
            if not md_out:
                md_out = str(result).strip()

    except Exception:
        md_out = (
            _fallback_llm(prompt, api_key=api_key, model=model)
            + "\n\n---\n"
            + "*(Note: CrewAI failed in this environment, so the app used a direct LLM fallback.)*"
        )

    # -----------------------------
    # Deterministic post-guardrails
    # -----------------------------
    # 1) If evaluator evidence is insufficient, withhold alignment in a meeting-safe way.
    if not has_eval_evidence:
        md_out = _replace_purpose_alignment_with_withheld_block(md_out)
        return md_out.strip()

    # 2) If rubric comment evidence is missing, force the criteria-linked checkbox to unchecked.
    if not has_rubric_comment:
        md_out = _set_checkbox(md_out, "Feedback linked to evaluation criteria", False)

    return md_out.strip()
