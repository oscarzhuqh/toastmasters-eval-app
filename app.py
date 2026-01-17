"""Toastmasters Evaluation Application (T.E.A.)

Multi-step Streamlit wizard:
1/4 Select Project Details
2/4 Load Project (from local markdown knowledge base)
3/4 Evaluation Form (rubric + general comments + notes)
4/4 Draft & Export (CrewAI draft + downloads)

Folder structure (repo root):
  knowledge/
    pathways/
      presentation_mastery.md
      dynamic_leadership.md
      engaging_humor.md
      motivational_strategies.md
      persuasive_influence.md
      visionary_communication.md

Optional PDF export:
- Add `reportlab` to requirements.txt on Streamlit Cloud to enable direct PDF download.
  Example: reportlab>=4.0
"""

from __future__ import annotations

import io
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st

# -------------------- OPTIONAL PDF (ReportLab) --------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Preformatted, SimpleDocTemplate, Spacer

    _PDF_OK = True
except Exception:
    _PDF_OK = False

# -------------------- OPTIONAL CREWAI --------------------
try:
    from crewai_eval import run_crewai_eval

    CREWAI_IMPORT_ERROR = ""
except Exception as e:
    run_crewai_eval = None
    CREWAI_IMPORT_ERROR = str(e)

# -------------------- CONFIG --------------------
APP_TITLE = "Toastmasters Evaluation Application"
APP_SUBTITLE = "Toastmasters Evaluation Assistant T.E.A."

KB_DIR = Path(__file__).parent / "knowledge" / "pathways"
LOGO_PATH = Path(__file__).parent / "TEA TM Logo.png"  # keep this filename in repo root

PATHWAY_FILES: Dict[str, str] = {
    "Dynamic Leadership": "dynamic_leadership.md",
    "Engaging Humor": "engaging_humor.md",
    "Motivational Strategies": "motivational_strategies.md",
    "Persuasive Influence": "persuasive_influence.md",
    "Presentation Mastery": "presentation_mastery.md",
    "Visionary Communication": "visionary_communication.md",
}

LEVELS = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]

# NOTE: Project dropdown list is driven per-pathway by reading the markdown.
# If a project is not in the markdown, it will NOT be shown (your preferred option A).

# Evaluation criteria used in the rubric expander + strength/improvement split.
SPEECH_EVALUATION_CRITERIA: Dict[str, Dict[int, str]] = {
    "Clarity": {
        5: "Is an exemplary public speaker who is always understood.",
        4: "Excels at communicating using the spoken word.",
        3: "Spoken language is clear and is easily understood.",
        2: "Spoken language is somewhat unclear or challenging to understand.",
        1: "Spoken language is unclear or not easily understood.",
    },
    "Vocal Variety": {
        5: "Uses the tools of tone, speed, and volume to perfection.",
        4: "Excels at using tone, speed, and volume as tools.",
        3: "Uses tone, speed, and volume as tools.",
        2: "Use of tone, speed, and volume requires further practice.",
        1: "Ineffective use of tone, speed, and volume.",
    },
    "Eye Contact": {
        5: "Uses eye contact to convey emotion and elicit response.",
        4: "Uses eye contact to gauge audience reaction and response.",
        3: "Effectively uses eye contact to engage audience.",
        2: "Eye contact with audience needs improvement.",
        1: "Makes little or no eye contact with audience.",
    },
    "Gestures": {
        5: "Fully integrates physical gestures with content to deliver an exemplary speech.",
        4: "Uses physical gestures as a tool to enhance speech.",
        3: "Uses physical gestures effectively.",
        2: "Uses somewhat distracting or limited gestures.",
        1: "Uses very distracting gestures or no gestures.",
    },
    "Audience Awareness": {
        5: "Engages audience completely and anticipates audience needs.",
        4: "Is fully aware of audience engagement/needs and responds effectively.",
        3: "Demonstrates awareness of audience engagement and needs.",
        2: "Audience engagement or awareness of audience requires further practice.",
        1: "Makes little or no attempt to engage audience or meet audience needs.",
    },
    "Comfort Level": {
        5: "Appears completely self-assured with the audience.",
        4: "Appears fully at ease with the audience.",
        3: "Appears comfortable with the audience.",
        2: "Appears uncomfortable with the audience.",
        1: "Appears highly uncomfortable with the audience.",
    },
    "Interest": {
        5: "Fully engages audience with exemplary, well-constructed content.",
        4: "Engages audience with highly compelling, well-constructed content.",
        3: "Engages audience with interesting, well-constructed content.",
        2: "Content is interesting but not well-constructed or is well-constructed but not interesting.",
        1: "Content is neither interesting nor well-constructed.",
    },
    "Well Supported": {
        5: "Delivers exemplary speech with a topic that is well-supported by content of the speech.",
        4: "Speech is excellent with a topic that is well-supported by content of the speech.",
        3: "Speech topic is well-supported by content of speech.",
        2: "Speech contains content that supports the topic though some content may seem disconnected.",
        1: "Speech content is unrelated to the topic of the speech.",
    },
}

RUBRIC_NAMES = list(SPEECH_EVALUATION_CRITERIA.keys())

SCORE_LEGEND = [
    "32–40 (or 32 and above) → Outstanding",
    "24–31 → Exceed Expectation of Speech Project",
    "16–23 → Meets Minimum Expectation of Speech Project",
    "8–15 → Needs Improvement",
]


# -------------------- HELPERS --------------------

def safe_text(s: str) -> str:
    return (s or "").strip()


def extract_level_block(md_path: Path, level: str) -> str | None:
    if not md_path.exists():
        return None

    lines = md_path.read_text(encoding="utf-8").splitlines()
    level_header = f"## {level}".lower()

    level_start = next((i for i, line in enumerate(lines) if line.strip().lower() == level_header), None)
    if level_start is None:
        return None

    level_end = next((i for i in range(level_start + 1, len(lines)) if lines[i].strip().startswith("## ")), len(lines))
    return "\n".join(lines[level_start:level_end])


def extract_level_focus(level_block: str) -> str | None:
    # supports: **Level focus (your words):** text
    m = re.search(r"\*\*Level focus.*?\*\*\s*:?‌?\s*(.+)", level_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def list_projects_in_level(level_block: str) -> List[str]:
    return re.findall(r"^###\s*Project:\s*(.+)\s*$", level_block, flags=re.IGNORECASE | re.MULTILINE)


def extract_project_block(level_block: str, project: str) -> str | None:
    lines = level_block.splitlines()
    project_header = f"### Project: {project}".lower()

    proj_start = next((i for i, line in enumerate(lines) if line.strip().lower() == project_header), None)
    if proj_start is None:
        return None

    proj_end = next(
        (i for i in range(proj_start + 1, len(lines)) if lines[i].strip().startswith("### Project:")),
        len(lines),
    )
    return "\n".join(lines[proj_start:proj_end])


def extract_field(proj_block: str, field_name: str) -> str | None:
    # supports: - **Purpose:** text  OR - **Speech length (optional)**: text
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*\s*:?‌?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def pdf_bytes_from_markdown(md_text: str, title: str = "Evaluation Draft") -> bytes | None:
    if not _PDF_OK:
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    story = []
    story.append(Preformatted(title, styles["Heading1"]))
    story.append(Spacer(1, 12))

    # Keep it simple + predictable: render markdown as preformatted text.
    story.append(Preformatted(md_text, styles["Code"]))

    doc.build(story)
    return buf.getvalue()


def step_header(page: str) -> None:
    steps: List[Tuple[str, str, str]] = [
        ("select", "Step 1/4", "Select Project Details"),
        ("load", "Step 2/4", "Load Project"),
        ("form", "Step 3/4", "Evaluation Form"),
        ("draft", "Step 4/4", "Draft & Export"),
    ]

    # Treat draft_loading as step 4 too
    normalized = "draft" if page in {"draft", "draft_loading"} else page
    current_i = {k: i for i, (k, _, _) in enumerate(steps)}.get(normalized, 0)

    cols = st.columns(4)
    for i, (k, step_label, step_title) in enumerate(steps):
        with cols[i]:
            checked = "✅" if i < current_i else ("☑️" if i == current_i else "")
            st.markdown(f"**{checked} {step_label}**  ")
            st.caption(step_title)

    st.progress((current_i + 1) / 4)


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("page", "select")

    # Meeting details
    ss.setdefault("speaker_name", "")
    ss.setdefault("evaluator_name", "")
    ss.setdefault("meeting_date", None)
    ss.setdefault("speech_title", "")

    # Selection
    ss.setdefault("pathway", "Dynamic Leadership")
    ss.setdefault("level", "Level 1")
    ss.setdefault("project", "")

    # Loaded project details
    ss.setdefault("level_focus", "")
    ss.setdefault("purpose", "")
    ss.setdefault("speech_len", "")

    # Rubric
    ss.setdefault("rubric_scores", {name: 3 for name in RUBRIC_NAMES})
    ss.setdefault("rubric_comments", {name: "" for name in RUBRIC_NAMES})

    # General comments
    ss.setdefault("excelled", "")
    ss.setdefault("work_on", "")
    ss.setdefault("challenge", "")

    # CrewAI notes (optional)
    ss.setdefault("notes", "")

    # Draft output
    ss.setdefault("draft_md", "")


def go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def get_md_path(pathway: str) -> Path:
    filename = PATHWAY_FILES.get(pathway, "")
    return KB_DIR / filename


def read_available_projects(pathway: str, level: str) -> List[str]:
    md_path = get_md_path(pathway)
    level_block = extract_level_block(md_path, level)
    if not level_block:
        return []
    return list_projects_in_level(level_block)


# -------------------- UI PAGES --------------------

def page_select() -> None:
    st.markdown(f"# {APP_TITLE}\n## {APP_SUBTITLE}")
    st.caption("NYP ITI123 Application Development Project")

    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=120)

    st.markdown("---")

    st.subheader("Chapter Meeting Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state.speaker_name = st.text_input("Speaker Name", value=st.session_state.speaker_name, placeholder="e.g., Oscar Zhu")
    with c2:
        st.session_state.evaluator_name = st.text_input(
            "Evaluator Name", value=st.session_state.evaluator_name, placeholder="e.g., Lee Ching Yuh"
        )
    with c3:
        st.session_state.meeting_date = st.date_input("Date of Chapter Meeting", value=st.session_state.meeting_date)

    st.session_state.speech_title = st.text_input(
        "Speech Title", value=st.session_state.speech_title, placeholder="e.g., Living with Dignity or Charity"
    )

    st.markdown("---")
    st.subheader("Select Project")

    pathway = st.selectbox("Select Pathway", list(PATHWAY_FILES.keys()), index=list(PATHWAY_FILES.keys()).index(st.session_state.pathway))
    level = st.selectbox("Select Level", LEVELS, index=LEVELS.index(st.session_state.level))

    # Update state
    st.session_state.pathway = pathway
    st.session_state.level = level

    md_path = get_md_path(pathway)
    if not md_path.exists():
        st.error(f"Markdown file not found for '{pathway}'. Expected: {md_path}")
        st.stop()

    available_projects = read_available_projects(pathway, level)
    if not available_projects:
        st.warning(
            f"No projects were found for **{pathway} → {level}** in `{md_path.name}`.\n\n"
            "Add headings in your markdown like: `### Project: <Project Name>` under the correct level."
        )
        st.caption(f"Using file: {md_path}")
        st.stop()

    # Keep selected project valid
    if st.session_state.project not in available_projects:
        st.session_state.project = available_projects[0]

    project = st.selectbox("Select Project", available_projects, index=available_projects.index(st.session_state.project))
    st.session_state.project = project

    st.caption(f"Using file: {md_path}")

    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("Get Details", type="primary"):
            go("load")

    with col_b:
        st.info("After you click **Get Details**, the app will load project details on the next page.")


def page_load() -> None:
    st.markdown("# Loading project")
    st.caption("Please wait... preparing your project (minimum 3 seconds).")

    # progress bar for at least ~3 seconds
    p = st.progress(0)
    for i in range(30):
        time.sleep(0.1)
        p.progress((i + 1) / 30)

    pathway = st.session_state.pathway
    level = st.session_state.level
    project = st.session_state.project

    md_path = get_md_path(pathway)
    level_block = extract_level_block(md_path, level)
    if not level_block:
        st.error(f"❌ Level '{level}' not found in {md_path.name}.")
        st.stop()

    proj_block = extract_project_block(level_block, project)
    if not proj_block:
        st.error(
            f"❌ '{project}' was not found under {level} for the '{pathway}' pathway.\n\n"
            "Please select the correct pathway/level OR add this project into the markdown file."
        )
        available = list_projects_in_level(level_block)
        if available:
            st.caption("Projects found in this pathway + level:")
            st.write(available)
        st.stop()

    # Store details
    st.session_state.level_focus = extract_level_focus(level_block) or "Not found"
    st.session_state.purpose = extract_field(proj_block, "Purpose") or "Not found"

    speech_len = (
        extract_field(proj_block, "Speech length (optional)")
        or extract_field(proj_block, "Speech length")
        or "Not found"
    )
    st.session_state.speech_len = speech_len

    go("form")


def _render_project_details_card() -> None:
    with st.container(border=True):
        st.markdown("### Pathway")
        st.write(st.session_state.pathway)

        st.markdown("---")
        st.markdown("### Level focus")
        st.write(st.session_state.level_focus)

        st.markdown("---")
        st.markdown("### Purpose")
        st.write(st.session_state.purpose)

        st.markdown("---")
        st.markdown("### Speech length")
        st.write(st.session_state.speech_len)


def _render_criteria_expander() -> str:
    """Returns a text blob of the criteria (used for CrewAI context)."""
    lines = []

    with st.expander("View Evaluation Criteria", expanded=False):
        st.markdown("### Evaluation Criteria")
        st.caption("These descriptions help you interpret each rating (1–5).")

        for crit in RUBRIC_NAMES:
            st.markdown(f"**{crit}**")
            for score in [5, 4, 3, 2, 1]:
                st.write(f"{score} — {SPEECH_EVALUATION_CRITERIA[crit][score]}")
            st.markdown("---")

    # Build criteria text for AI
    for crit in RUBRIC_NAMES:
        lines.append(f"{crit}:")
        for score in [5, 4, 3, 2, 1]:
            lines.append(f"  {score} - {SPEECH_EVALUATION_CRITERIA[crit][score]}")
        lines.append("")

    return "\n".join(lines).strip()


def _render_rubric_table() -> Tuple[List[str], List[str], int]:
    """Renders one row per criterion using columns; returns strengths, improvements, total score."""

    st.markdown("## Rubric Ratings (1–5)")
    st.caption("Rule: ratings 4–5 → Strengths, ratings 1–3 → Areas for improvement.")

    # Header row
    h1, h2, h3 = st.columns([2.4, 2.6, 3.0])
    with h1:
        st.markdown("**Criteria**")
    with h2:
        st.markdown("**Rating (1–5)**")
    with h3:
        st.markdown("**Comment**")

    st.markdown("---")

    strengths: List[str] = []
    improvements: List[str] = []

    for name in RUBRIC_NAMES:
        c1, c2, c3 = st.columns([2.4, 2.6, 3.0])
        with c1:
            st.markdown(f"**{name}**")
        with c2:
            key = f"score_{name}"
            default = int(st.session_state.rubric_scores.get(name, 3))
            st.session_state.rubric_scores[name] = st.radio(
                label=f"{name} rating",
                options=[1, 2, 3, 4, 5],
                index=[1, 2, 3, 4, 5].index(default),
                horizontal=True,
                label_visibility="collapsed",
                key=key,
            )
        with c3:
            ckey = f"comment_{name}"
            st.session_state.rubric_comments[name] = st.text_area(
                label=f"{name} comment",
                value=st.session_state.rubric_comments.get(name, ""),
                placeholder="Optional short comment...",
                height=56,
                label_visibility="collapsed",
                key=ckey,
            )

        score = int(st.session_state.rubric_scores[name])
        if score >= 4:
            strengths.append(f"{name} ({score}/5)")
        else:
            improvements.append(f"{name} ({score}/5)")

    total_score = sum(int(st.session_state.rubric_scores[n]) for n in RUBRIC_NAMES)
    return strengths, improvements, total_score


def _score_label(total: int) -> str:
    if total >= 32:
        return "Outstanding"
    if total >= 24:
        return "Exceed Expectation of Speech Project"
    if total >= 16:
        return "Meets Minimum Expectation of Speech Project"
    return "Needs Improvement"


def page_form() -> None:
    st.markdown("# Evaluation Form")

    st.subheader("Project Details")
    _render_project_details_card()

    st.markdown("---")

    criteria_text = _render_criteria_expander()

    strengths, improvements, total_score = _render_rubric_table()
    label = _score_label(total_score)

    st.markdown("---")

    # Strengths vs Improvements + total score + legend
    left, right = st.columns(2)
    with left:
        st.markdown("## Strengths (4–5)")
        if strengths:
            st.write("\n".join([f"• {s}" for s in strengths]))
        else:
            st.write("• (none selected)")

    with right:
        st.markdown("## Areas for Improvement (1–3)")
        if improvements:
            st.write("\n".join([f"• {s}" for s in improvements]))
        else:
            st.write("• (none selected)")

    st.markdown(f"### Total score: **{total_score}/40** — **{label}**")
    with st.expander("Score Legend", expanded=False):
        for line in SCORE_LEGEND:
            st.write(f"• {line}")

    st.markdown("---")

    # General comments
    st.markdown("## General Comments – By Project Speech Evaluator")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.excelled = st.text_area(
            "✅ You excelled at:",
            value=st.session_state.excelled,
            height=120,
            placeholder="e.g., Clear structure, strong eye contact...",
        )
    with c2:
        st.session_state.work_on = st.text_area(
            "🔧 You may want to work on:",
            value=st.session_state.work_on,
            height=120,
            placeholder="e.g., Vary pace, add stronger gestures...",
        )

    st.session_state.challenge = st.text_area(
        "🎯 To challenge yourself:",
        value=st.session_state.challenge,
        height=120,
        placeholder="e.g., Try a stronger opening hook next time...",
    )

    st.markdown("---")

    # Evaluator notes for AI
    st.markdown("## Evaluator Notes (optional — input for CrewAI)")
    st.caption(
        "Use this box for any extra raw notes you captured during the speech. "
        "If you already filled the **General Comments** and rubric, this can be left blank."
    )

    st.session_state.notes = st.text_area(
        "Paste your rough notes (bullet points ok):",
        value=st.session_state.notes,
        height=160,
        placeholder="e.g., Opening story was engaging; watch pacing in middle; nice callback at end...",
    )

    st.markdown("---")

    # Navigation + generation
    col_l, col_r = st.columns([1, 2])
    with col_l:
        if st.button("Back"):
            go("select")

    with col_r:
        if st.button("Generate Evaluation Draft (CrewAI)", type="primary"):
            # Validate: require at least SOME content in rubric comments/general comments/notes
            any_comment = any(safe_text(v) for v in st.session_state.rubric_comments.values())
            any_general = any(
                [
                    safe_text(st.session_state.excelled),
                    safe_text(st.session_state.work_on),
                    safe_text(st.session_state.challenge),
                    safe_text(st.session_state.notes),
                ]
            )
            if not (any_comment or any_general):
                st.warning("Please add at least one comment (rubric comment, general comment, or notes) before generating.")
                st.stop()

            # Build notes payload for CrewAI
            speaker = safe_text(st.session_state.speaker_name)
            evaluator = safe_text(st.session_state.evaluator_name)
            date_str = str(st.session_state.meeting_date) if st.session_state.meeting_date else ""
            speech_title = safe_text(st.session_state.speech_title)

            rubric_lines = []
            for name in RUBRIC_NAMES:
                sc = int(st.session_state.rubric_scores[name])
                cm = safe_text(st.session_state.rubric_comments.get(name, ""))
                if cm:
                    rubric_lines.append(f"- {name}: {sc}/5 — {cm}")
                else:
                    rubric_lines.append(f"- {name}: {sc}/5")

            notes_payload = "\n".join(
                [
                    f"Speaker: {speaker}",
                    f"Evaluator: {evaluator}",
                    f"Meeting date: {date_str}",
                    f"Speech title: {speech_title}",
                    "",
                    "Rubric ratings:",
                    *rubric_lines,
                    "",
                    "General comments:",
                    f"- You excelled at: {safe_text(st.session_state.excelled)}",
                    f"- You may want to work on: {safe_text(st.session_state.work_on)}",
                    f"- To challenge yourself: {safe_text(st.session_state.challenge)}",
                    "",
                    "Extra notes (optional):",
                    safe_text(st.session_state.notes),
                ]
            ).strip()

            st.session_state.pending = {
                "notes": notes_payload,
                "pathway": st.session_state.pathway,
                "level": st.session_state.level,
                "project": st.session_state.project,
                "level_focus": st.session_state.level_focus,
                "purpose": st.session_state.purpose,
                "speech_len": st.session_state.speech_len,
                "criteria_text": criteria_text,
                "strengths": strengths,
                "improvements": improvements,
                "total_score": total_score,
                "score_label": label,
                "speaker_name": speaker,
                "evaluator_name": evaluator,
                "meeting_date": date_str,
                "speech_title": speech_title,
            }

            go("draft_loading")


def page_draft_loading() -> None:
    st.markdown("# Generating evaluation draft")
    st.caption("Please wait... preparing your draft (minimum 3 seconds).")

    p = st.progress(0)
    for i in range(30):
        time.sleep(0.1)
        p.progress((i + 1) / 30)

    pending = st.session_state.get("pending", {})
    if not pending:
        st.error("Something went wrong: no pending request found. Please go back and generate again.")
        st.stop()

    if run_crewai_eval is None:
        st.session_state.draft_md = "CrewAI module failed to import.\n\n" + (CREWAI_IMPORT_ERROR or "")
        go("draft")
        return

    with st.spinner("Running CrewAI..."):
        # NOTE: we pass named args that crewai_eval.py supports (and can safely ignore extras via **kwargs).
        output = run_crewai_eval(
            notes=pending.get("notes", ""),
            pathway=pending.get("pathway", ""),
            level=pending.get("level", ""),
            project=pending.get("project", ""),
            level_focus=pending.get("level_focus", ""),
            purpose=pending.get("purpose", ""),
            speech_len=pending.get("speech_len", ""),
            criteria_text=pending.get("criteria_text", ""),
            strengths=pending.get("strengths", []),
            improvements=pending.get("improvements", []),
            total_score=pending.get("total_score", 0),
            score_label=pending.get("score_label", ""),
            speaker_name=pending.get("speaker_name", ""),
            evaluator_name=pending.get("evaluator_name", ""),
            meeting_date=pending.get("meeting_date", ""),
            speech_title=pending.get("speech_title", ""),
        )

    st.session_state.draft_md = output or ""
    go("draft")


def page_draft() -> None:
    st.markdown("# Draft & Export")

    md = st.session_state.get("draft_md", "").strip()
    if not md:
        st.warning("No draft found yet. Please go back and generate one.")
        if st.button("Back"):
            go("form")
        st.stop()

    st.subheader("Evaluation Draft")
    st.markdown(md)

    st.markdown("---")
    st.subheader("Export")

    filename_base = "evaluation_draft"
    if safe_text(st.session_state.speaker_name):
        filename_base = safe_text(st.session_state.speaker_name).replace(" ", "_") + "_evaluation"

    # Markdown download
    st.download_button(
        "Download Markdown (.md)",
        data=md.encode("utf-8"),
        file_name=f"{filename_base}.md",
        mime="text/markdown",
    )

    # Print-friendly HTML download (then browser Print -> Save as PDF)
    html = (
        "<html><head><meta charset='utf-8'>"
        "<style>body{font-family:Arial,Helvetica,sans-serif;max-width:800px;margin:24px auto;line-height:1.5}"
        "pre{white-space:pre-wrap;font-family:Consolas,monospace;background:#f6f8fa;padding:12px;border-radius:8px}"
        "</style></head><body>"
        f"<h1>{APP_TITLE} - Draft</h1>"
        "<pre>" + (md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")) + "</pre>"
        "</body></html>"
    )

    st.download_button(
        "Download Print-HTML (.html)",
        data=html.encode("utf-8"),
        file_name=f"{filename_base}.html",
        mime="text/html",
    )
    st.caption("For PDF (Option A): open the HTML → Print → Save as PDF.")

    # Direct PDF download
    pdf = pdf_bytes_from_markdown(md_text=md, title=f"{APP_TITLE} - Draft")
    if pdf:
        st.download_button(
            "Download PDF (.pdf)",
            data=pdf,
            file_name=f"{filename_base}.pdf",
            mime="application/pdf",
        )
        st.caption("PDF (Option B): generated directly by the app (ReportLab).")
    else:
        st.info(
            "Direct PDF download is disabled because `reportlab` is not installed in this environment. "
            "Add `reportlab` to your `requirements.txt` and redeploy."
        )

    st.markdown("---")
    if st.button("Back"):
        go("form")


# -------------------- MAIN --------------------

def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="☕", layout="centered")
    init_state()

    page = st.session_state.page
    step_header(page)

    if page == "select":
        page_select()
    elif page == "load":
        page_load()
    elif page == "form":
        page_form()
    elif page == "draft_loading":
        page_draft_loading()
    elif page == "draft":
        page_draft()
    else:
        st.session_state.page = "select"
        page_select()


if __name__ == "__main__":
    main()
