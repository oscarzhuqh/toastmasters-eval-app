"""CrewAI evaluation generator for Toastmasters Evaluation Assistant (T.E.A.).



# ==================== Evidence guardrails (deterministic) ====================

_PLACEHOLDERS = {"", "-", "–", "—", "n/a", "na", "none", "nil", "null", "no", "nope", "not sure", "unsure", "tbc", "?", "??", "...", "…"}

def _is_placeholder(s: str) -> bool:
    s = (s or "").strip().lower()
    return s in _PLACEHOLDERS

def _extract_notes_section(notes_payload: str, header: str) -> str:
    """Extract a section by exact header line (case-insensitive) from the notes payload."""
    if not notes_payload:
        return ""
    pat = rf"^\s*{re.escape(header)}\s*$"
    m = re.search(pat, notes_payload, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""
    after = notes_payload[m.end():]
    # Stop at next blank line followed by a label-like header ending with ':'
    parts = re.split(r"\n\s*\n(?=\S[^\n]{0,60}:\s*$)", after, maxsplit=1)
    return parts[0].strip()

def _has_rubric_comments(notes_payload: str) -> bool:
    rc = _extract_notes_section(notes_payload, "Rubric comments (verbatim):")
    if not rc:
        return False
    for ln in [l.strip() for l in rc.splitlines() if l.strip()]:
        cleaned = re.sub(r"^[\s\-•]+", "", ln)
        if cleaned and not _is_placeholder(cleaned) and len(re.findall(r"[A-Za-z]", cleaned)) >= 3:
            return True
    return False

def _has_substantive_evaluator_evidence(notes_payload: str) -> bool:
    """Meaningful evaluator evidence must come from evaluator free-text (not project metadata or auto rubric summaries)."""
    chunks = []

    # General comment boxes
    gc = _extract_notes_section(notes_payload, "General comments:")
    if gc:
        for sub in ["You excelled at:", "You may want to work on:", "To challenge yourself:"]:
            m = re.search(rf"^{re.escape(sub)}\s*$", gc, flags=re.IGNORECASE | re.MULTILINE)
            if m:
                seg = gc[m.end():]
                seg = re.split(r"^\s*(You excelled at:|You may want to work on:|To challenge yourself:)\s*$",
                               seg, maxsplit=1, flags=re.IGNORECASE | re.MULTILINE)[0]
                chunks.append(seg.strip())

    # Per-criterion rubric comments (verbatim)
    rc = _extract_notes_section(notes_payload, "Rubric comments (verbatim):")
    if rc:
        chunks.append(rc.strip())

    for c in chunks:
        cleaned = re.sub(r"^[\s\-•]+", "", (c or "").strip())
        if cleaned and not _is_placeholder(cleaned) and len(re.findall(r"[A-Za-z]", cleaned)) >= 3:
            return True
    return False

def _replace_or_append_purpose_alignment(md_text: str, new_block: str) -> str:
    md = (md_text or "").rstrip() + "\n"
    m = re.search(r"^#{1,3}\s+Purpose\s+Alignment\s*$", md, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return md.rstrip() + "\n\n" + new_block.strip() + "\n"
    start = m.start()
    after = md[m.end():]
    # Cut until next heading
    parts = re.split(r"^#{1,3}\s+", after, maxsplit=1, flags=re.MULTILINE)
    tail = ""
    if len(parts) > 1:
        tail = after[len(parts[0]):]  # includes the next heading marker
    return md[:start].rstrip() + "\n\n" + new_block.strip() + "\n\n" + tail.lstrip()

def _force_checklist_states(md_text: str, states: dict) -> str:
    md = md_text or ""
    m = re.search(r"^#{1,3}\s+Purpose\s+Alignment\s*$", md, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return md
    start = m.end()
    after = md[start:]
    parts = re.split(r"^#{1,3}\s+", after, maxsplit=1, flags=re.MULTILINE)
    section = parts[0]
    tail = after[len(section):]

    def repl_line(line: str) -> str:
        for label, val in states.items():
            if re.match(rf"^\s*-\s*\[(x| )\]\s*{re.escape(label)}\s*$", line, flags=re.IGNORECASE):
                mark = "x" if val else " "
                return re.sub(r"\[(x| )\]", f"[{mark}]", line, count=1, flags=re.IGNORECASE)
        return line

    new_section = "\n".join(repl_line(ln) for ln in section.splitlines())
    return md[:start] + new_section + tail

Designed to be robust:
- Reads API key/model from env vars or Streamlit secrets.
- Attempts to use CrewAI.
- If CrewAI isn't available or fails due to version mismatches, falls back to a single LLM call.

App expects:
    from crewai_eval import run_crewai_eval
"""

from __future__ import annotations

import os
import re

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
1) Short opening (1-2 sentences) that references the project purpose.
2) Strengths section (bullets) - must map back to rubric strengths.
3) Areas for improvement (bullets) - must map back to rubric areas.
4) One actionable challenge goal (1-2 sentences).
5) Purpose Alignment (must be present):
   - 1–2 sentence summary of how the speech aligns to Purpose + Level focus.
   - Checkbox-style checklist (Markdown task list):
     - [ ] Purpose clearly addressed
     - [ ] Level focus demonstrated
     - [ ] Feedback linked to evaluation criteria
     - [ ] Balanced commendations + improvements
     - [ ] Actionable next step provided
   - 2–3 short bullets explaining *why* the above items are checked/unchecked.

Rules:
- Be specific (use examples where available), but do not invent detail
- Do not infer speech content from the speech title alone. If evaluator evidence is missing, state that alignment is withheld.s.
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

        # Normalize CrewAI result into a markdown string
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

        # -------------------- Deterministic guardrails --------------------
        has_eval_evidence = _has_substantive_evaluator_evidence(notes)
        has_rubric_comments = _has_rubric_comments(notes)

        if not has_eval_evidence:
            conservative = """## Purpose Alignment
Alignment is **withheld** because the evaluator provided insufficient evidence (no substantive notes/comments). Please add specific observations to enable evidence-backed alignment.

- [ ] Purpose clearly addressed
- [ ] Level focus demonstrated
- [ ] Feedback linked to evaluation criteria
- [ ] Balanced commendations + improvements
- [ ] Actionable next step provided
"""
            md_out = _replace_or_append_purpose_alignment(md_out, conservative)
        else:
            if not has_rubric_comments:
                md_out = _force_checklist_states(md_out, {"Feedback linked to evaluation criteria": False})

        return md_out

    except Exception:
        # --- Fallback ---
        md_out = (
            _fallback_llm(prompt, api_key=api_key, model=model)
            + "\n\n---\n"
            + "*(Note: CrewAI failed in this environment, so the app used a direct LLM fallback.)*"
        )

        has_eval_evidence = _has_substantive_evaluator_evidence(notes)
        has_rubric_comments = _has_rubric_comments(notes)

        if not has_eval_evidence:
            conservative = """## Purpose Alignment
Alignment is **withheld** because the evaluator provided insufficient evidence (no substantive notes/comments). Please add specific observations to enable evidence-backed alignment.

- [ ] Purpose clearly addressed
- [ ] Level focus demonstrated
- [ ] Feedback linked to evaluation criteria
- [ ] Balanced commendations + improvements
- [ ] Actionable next step provided
"""
            md_out = _replace_or_append_purpose_alignment(md_out, conservative)
        else:
            if not has_rubric_comments:
                md_out = _force_checklist_states(md_out, {"Feedback linked to evaluation criteria": False})

        return md_out
