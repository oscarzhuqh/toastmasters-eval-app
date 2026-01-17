import time
import re
import html
from pathlib import Path

import streamlit as st

# ==================== CrewAI import (safe) ====================
try:
    from crewai_eval import run_crewai_eval
except Exception as e:
    run_crewai_eval = None
    CREWAI_IMPORT_ERROR = str(e)
else:
    CREWAI_IMPORT_ERROR = ""


# ==================== CONFIG ====================
APP_DIR = Path(__file__).parent
KB_DIR = APP_DIR / "knowledge" / "pathways"

PATHWAY_FILES = {
    "Dynamic Leadership": "dynamic_leadership.md",
    "Engaging Humor": "engaging_humor.md",
    "Motivational Strategies": "motivational_strategies.md",
    "Persuasive Influence": "persuasive_influence.md",
    "Presentation Mastery": "presentation_mastery.md",
    "Visionary Communication": "visionary_communication.md",
}

LEVELS = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]

LOGO_CANDIDATES = [
    APP_DIR / "TEA TM Logo.png",
    APP_DIR / "assets" / "TEA TM Logo.png",
    APP_DIR / "assets" / "logo.png",
]

# Evaluation criteria (Ice Breaker)
SPEECH_EVALUATION_CRITERIA = {
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
        3: "Speech topic is well-supported by content of the speech.",
        2: "Speech contains content that supports the topic though some content may seem disconnected.",
        1: "Speech content is unrelated to the topic of the speech.",
    },
}

SCORE_LEGEND = [
    (32, 40, "Outstanding"),
    (24, 31, "Exceed Expectation of Speech Project"),
    (16, 23, "Meets Minimum Expectation of Speech Project"),
    (8, 15, "Needs Improvement"),
]


# ==================== Helpers ====================

def _find_logo_path() -> Path | None:
    for p in LOGO_CANDIDATES:
        if p.exists():
            return p
    return None


def set_page(next_page: str) -> None:
    st.session_state.page = next_page


def extract_level_block(md_path: Path, level: str) -> str | None:
    if not md_path.exists():
        return None

    lines = md_path.read_text(encoding="utf-8").splitlines()
    level_header = f"## {level}"

    level_start = next((i for i, line in enumerate(lines) if line.strip().lower() == level_header.lower()), None)
    if level_start is None:
        return None

    level_end = next((i for i in range(level_start + 1, len(lines)) if lines[i].strip().startswith("## ")), len(lines))
    return "\n".join(lines[level_start:level_end])


def list_projects_in_level(md_path: Path, level: str) -> list[str]:
    level_block = extract_level_block(md_path, level)
    if not level_block:
        return []

    projects = re.findall(r"^###\s*Project:\s*(.+)\s*$", level_block, flags=re.IGNORECASE | re.MULTILINE)
    # keep order, de-dupe
    seen = set()
    out: list[str] = []
    for p in projects:
        name = p.strip()
        if name and name.lower() not in seen:
            out.append(name)
            seen.add(name.lower())
    return out


def extract_level_focus(level_block: str) -> str | None:
    m = re.search(r"\*\*Level focus.*?\*\*\s*:?\s*(.+)", level_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_project_block(level_block: str, project: str) -> str | None:
    lines = level_block.splitlines()
    header = f"### Project: {project}"

    start = next((i for i, line in enumerate(lines) if line.strip().lower() == header.lower()), None)
    if start is None:
        return None

    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("### Project:")), len(lines))
    return "\n".join(lines[start:end])


def extract_field(proj_block: str, field_name: str) -> str | None:
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*?\s*:?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def score_label(total: int) -> str:
    for lo, hi, label in SCORE_LEGEND:
        if lo <= total <= hi:
            return label
    return ""


def min3s_progress(message: str = "Loading…") -> None:
    st.write(message)
    p = st.progress(0)
    # 3.0s total (approx)
    steps = 30
    for i in range(steps):
        time.sleep(0.1)
        p.progress(int((i + 1) / steps * 100))


def make_printable_html(title: str, body_markdown: str) -> str:
    escaped = html.escape(body_markdown)
    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1,h2,h3 {{ margin: 0.6em 0 0.3em; }}
    .meta {{ color: #555; font-size: 12px; margin-bottom: 16px; }}
    pre {{ white-space: pre-wrap; word-wrap: break-word; font-size: 13px; line-height: 1.4; }}
    @media print {{ body {{ margin: 12mm; }} }}
  </style>
</head>
<body>
  <h2>{html.escape(title)}</h2>
  <div class='meta'>Tip: Use your browser Print → Save as PDF.</div>
  <pre>{escaped}</pre>
</body>
</html>"""


# ==================== Page setup ====================
st.set_page_config(page_title="Toastmasters Evaluation Application", page_icon="🫖", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "intro"

# storage
st.session_state.setdefault("meeting", {})
st.session_state.setdefault("project_details", {})
st.session_state.setdefault("rubric", {})
st.session_state.setdefault("crewai_output", "")

page = st.session_state.page

# ==================== Header ====================
logo_path = _find_logo_path()
if logo_path:
    st.image(str(logo_path), width=110)

st.markdown("# Toastmasters Evaluation Application (T.E.A.) ")
st.caption("The objective of this project is to build a web-based Toastmasters Evaluation Assistant (T.E.A.) that retrieves Pathways project objectives from a local knowledge base, captures rubric ratings and evaluator notes, and generates a structured, editable evaluation draft with export support (e.g., PDF/Markdown) to improve speed and consistency of speech evaluations.")
st.caption("NYP ITI123 Application Development Project by Zhu Qihui, Oscar 9801937V")

# Step indicator
steps = [
    ("intro", "Step 1/4", "Select Project Details"),
    ("loading", "Step 2/4", "Load Project"),
    ("evaluation", "Step 3/4", "Evaluation Form"),
    ("draft", "Step 4/4", "Draft & Export"),
]
step_idx = {k: i for i, (k, _, _) in enumerate(steps)}
current_i = step_idx.get(page, 0)

cols = st.columns(4)
for i, (k, label, desc) in enumerate(steps):
    with cols[i]:
        icon = "✅" if i < current_i else ("☑️" if i == current_i else "")
        st.markdown(f"**{icon} {label}**\n\n{desc}")

st.progress(int((current_i + 1) / 4 * 100))

st.write("---")


# ==================== Step 1: Intro ====================
if page == "intro":
    st.subheader("Chapter Meeting Details")

    c1, c2, c3 = st.columns(3)
    with c1:
        speaker = st.text_input("Speaker Name", value=st.session_state.meeting.get("speaker", ""), placeholder="e.g., Oscar Zhu")
    with c2:
        evaluator = st.text_input("Evaluator Name", value=st.session_state.meeting.get("evaluator", ""), placeholder="e.g., Lee Ching Yuh")
    with c3:
        meeting_date = st.date_input("Date of Chapter Meeting", value=st.session_state.meeting.get("meeting_date", None))

    speech_title = st.text_input("Speech Title", value=st.session_state.meeting.get("speech_title", ""), placeholder="e.g., Living with Dignity or Charity")

    st.write("---")
    st.subheader("Select Project")

    pathway = st.selectbox("Select Pathway", list(PATHWAY_FILES.keys()), index=0)
    level = st.selectbox("Select Level", LEVELS, index=0)

    md_path = KB_DIR / PATHWAY_FILES[pathway]
    available_projects = list_projects_in_level(md_path, level) if md_path.exists() else []

    if not md_path.exists():
        st.error(f"Markdown not found: {md_path}. Create it under knowledge/pathways/")
        st.stop()

    if not available_projects:
        st.warning(
            "No projects found for this Pathway + Level in your markdown yet. "
            "Add headings like `### Project: Ice Breaker` under `## Level 1`."
        )
        with st.expander("Projects found in this markdown file"):
            text = md_path.read_text(encoding="utf-8")
            all_projects = re.findall(r"^###\s*Project:\s*(.+)\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
            st.write(all_projects)
        st.stop()

    project = st.selectbox("Select Project", available_projects)

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Get Details", type="primary"):
            # save meeting
            st.session_state.meeting = {
                "speaker": speaker,
                "evaluator": evaluator,
                "meeting_date": meeting_date,
                "speech_title": speech_title,
            }
            st.session_state.project_details = {
                "pathway": pathway,
                "level": level,
                "project": project,
                "md_path": str(md_path),
            }
            set_page("loading")
            st.rerun()

    with colB:
        if st.button("Reset"):
            st.session_state.clear()
            st.rerun()


# ==================== Step 2: Loading ====================
elif page == "loading":
    st.subheader("Loading project details")
    min3s_progress("Please wait… loading selected project (minimum 3 seconds).")

    details = st.session_state.get("project_details", {})
    md_path = Path(details.get("md_path", ""))
    level = details.get("level", "")
    project = details.get("project", "")
    pathway = details.get("pathway", "")

    if not md_path.exists():
        st.error(f"Markdown file not found: {md_path}")
        if st.button("Back"):
            set_page("intro")
            st.rerun()
        st.stop()

    level_block = extract_level_block(md_path, level)
    if not level_block:
        st.error(f"Level '{level}' not found in {md_path.name}. Add a heading like: `## {level}`")
        if st.button("Back"):
            set_page("intro")
            st.rerun()
        st.stop()

    proj_block = extract_project_block(level_block, project)
    if not proj_block:
        st.error(
            f"'{project}' was not found under {level} for '{pathway}'. "
            "Please select a different project or add it into the markdown file."
        )
        with st.expander("Projects found in this pathway + level"):
            st.write(list_projects_in_level(md_path, level))
        if st.button("Back"):
            set_page("intro")
            st.rerun()
        st.stop()

    level_focus = extract_level_focus(level_block) or "Not found"
    purpose = extract_field(proj_block, "Purpose") or "Not found"
    speech_len = (
        extract_field(proj_block, "Speech length (optional)")
        or extract_field(proj_block, "Speech length")
        or "Not found"
    )

    st.session_state.project_details.update(
        {
            "level_focus": level_focus,
            "purpose": purpose,
            "speech_len": speech_len,
        }
    )

    set_page("evaluation")
    st.rerun()


# ==================== Step 3: Evaluation Form ====================
elif page == "evaluation":
    d = st.session_state.get("project_details", {})
    meeting = st.session_state.get("meeting", {})

    st.subheader("Project Details")

    with st.container(border=True):
        st.markdown(f"**Pathway**: {d.get('pathway','')}")
        st.markdown(f"**Level**: {d.get('level','')}")
        st.markdown(f"**Project**: {d.get('project','')}")
        st.markdown("---")
        st.markdown("**Level focus**")
        st.write(d.get("level_focus", ""))
        st.markdown("---")
        st.markdown("**Purpose**")
        st.write(d.get("purpose", ""))
        st.markdown("---")
        st.markdown("**Speech length**")
        st.write(d.get("speech_len", ""))

    st.write("---")

    st.subheader("Rubric Ratings (1–5)")
    st.caption("Rule: ratings 4–5 → Strengths, ratings 1–3 → Areas for improvement. Default is 3.")

    with st.expander("View Evaluation Criteria (Ice Breaker)"):
        for crit, mapping in SPEECH_EVALUATION_CRITERIA.items():
            st.markdown(f"### {crit}")
            for s in [5, 4, 3, 2, 1]:
                st.markdown(f"**{s}** — {mapping[s]}")

    # header row
    h1, h2, h3 = st.columns([2.2, 2.3, 3.5])
    with h1:
        st.markdown("**Criteria**")
    with h2:
        st.markdown("**Rating (1–5)**")
        st.caption("5 4 3 2 1")
    with h3:
        st.markdown("**Comment**")

    ratings: dict[str, int] = {}
    comments: dict[str, str] = {}

    for crit in SPEECH_EVALUATION_CRITERIA.keys():
        c1, c2, c3 = st.columns([2.2, 2.3, 3.5])
        with c1:
            st.markdown(f"**{crit}**")
        with c2:
            # default rating = 3
            r = st.radio(
                label=f"rating_{crit}",
                options=[5, 4, 3, 2, 1],
                index=2,
                horizontal=True,
                label_visibility="collapsed",
                key=f"rate_{crit}",
            )
        with c3:
            cm = st.text_input(
                label=f"comment_{crit}",
                value="",
                placeholder="Optional (short notes)",
                label_visibility="collapsed",
                key=f"comment_{crit}",
            )
        ratings[crit] = int(r)
        comments[crit] = cm.strip()

    total = sum(ratings.values())
    label = score_label(total)

    st.write("---")
    st.subheader("Score Summary")
    st.markdown(f"**Total accumulated score:** {total} / 40")
    if label:
        st.markdown(f"**Overall band:** {label}")

    st.markdown("**Legend**")
    for lo, hi, lab in SCORE_LEGEND:
        st.markdown(f"- **{lo}–{hi}** → {lab}")

    strengths = [f"{k} ({v}/5)" for k, v in ratings.items() if v >= 4]
    improvements = [f"{k} ({v}/5)" for k, v in ratings.items() if v <= 3]

    cA, cB = st.columns(2)
    with cA:
        st.markdown("### Strengths (4–5)")
        if strengths:
            st.write("\n".join([f"- {x}" for x in strengths]))
        else:
            st.write("- (none selected)")

    with cB:
        st.markdown("### Areas for Improvement (1–3)")
        if improvements:
            st.write("\n".join([f"- {x}" for x in improvements]))
        else:
            st.write("- (none selected)")

    st.write("---")
    st.subheader("General Comments – By Project Speech Evaluator")

    gc1, gc2 = st.columns(2)
    with gc1:
        excelled = st.text_area("✅ You excelled at:", height=120, placeholder="e.g., Clear structure, strong eye contact…")
    with gc2:
        work_on = st.text_area("🛠️ You may want to work on:", height=120, placeholder="e.g., Vary pace, add stronger gestures…")

    challenge = st.text_area("🎯 To challenge yourself:", height=120, placeholder="e.g., Try a stronger opening hook next time…")

    st.write("---")
    st.subheader("Evaluator Notes (input for CrewAI)")
    notes = st.text_area("Paste your rough notes (bullet points ok):", height=160)

    # Build criteria text for CrewAI
    criteria_lines = []
    for crit, r in ratings.items():
        definition = SPEECH_EVALUATION_CRITERIA[crit].get(r, "")
        cm = comments.get(crit, "")
        if cm:
            criteria_lines.append(f"- {crit}: {r}/5 — {definition} (Comment: {cm})")
        else:
            criteria_lines.append(f"- {crit}: {r}/5 — {definition}")
    criteria_text = "\n".join(criteria_lines)

    notes_payload = "\n".join(
        [
            f"Speaker: {meeting.get('speaker','')}",
            f"Evaluator: {meeting.get('evaluator','')}",
            f"Date: {meeting.get('meeting_date','')}",
            f"Speech title: {meeting.get('speech_title','')}",
            "",
            "Rubric ratings summary:",
            criteria_text,
            "",
            f"Total score: {total}/40 ({label})" if label else f"Total score: {total}/40",
            "",
            "General comments (drafted by evaluator):",
            f"You excelled at: {excelled}",
            f"You may want to work on: {work_on}",
            f"To challenge yourself: {challenge}",
            "",
            "Additional evaluator notes:",
            notes,
        ]
    ).strip()

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Back", key="back_eval"):
            set_page("intro")
            st.rerun()

    with col2:
        if st.button("Generate Evaluation Draft (CrewAI)", type="primary"):
            if not notes_payload.strip():
                st.warning("Please enter at least some notes.")
                st.stop()

            st.session_state.pending_crewai = {
                "notes_payload": notes_payload,
                "pathway": d.get("pathway", ""),
                "level": d.get("level", ""),
                "project": d.get("project", ""),
                "level_focus": d.get("level_focus", ""),
                "purpose": d.get("purpose", ""),
                "speech_len": d.get("speech_len", ""),
                "criteria_text": criteria_text,
                "total_score": total,
                "score_label": label,
            }
            set_page("draft_loading")
            st.rerun()


# ==================== Step 4A: Draft Loading ====================
elif page == "draft_loading":
    st.subheader("Generating evaluation draft")
    min3s_progress("Please wait… preparing your draft (minimum 3 seconds).")

    pending = st.session_state.get("pending_crewai", {})

    if not pending:
        st.error("Nothing to generate yet. Please go back and fill the evaluation form.")
        if st.button("Back"):
            set_page("evaluation")
            st.rerun()
        st.stop()

    if run_crewai_eval is None:
        output = "CrewAI module failed to import.\n\n" + (CREWAI_IMPORT_ERROR or "")
    else:
        with st.spinner("Running CrewAI…"):
            output = run_crewai_eval(
                notes=pending.get("notes_payload", ""),
                pathway=pending.get("pathway", ""),
                level=pending.get("level", ""),
                project=pending.get("project", ""),
                level_focus=pending.get("level_focus", ""),
                purpose=pending.get("purpose", ""),
                speech_len=pending.get("speech_len", ""),
                criteria_text=pending.get("criteria_text", ""),
                total_score=pending.get("total_score", ""),
                score_label=pending.get("score_label", ""),
            )

    st.session_state.crewai_output = output
    set_page("draft")
    st.rerun()


# ==================== Step 4B: Draft & Export ====================
elif page == "draft":
    output = st.session_state.get("crewai_output", "")
    if not output:
        st.warning("No draft found yet. Generate one first.")

    st.subheader("Draft & Export")

    # Print-friendly container
    st.markdown(
        """
        <style>
          /* slightly smaller overall look */
          .block-container { max-width: 860px; padding-top: 1.6rem; }
          @media print { .stButton, .stDownloadButton, header, footer { display:none !important; } }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("### Evaluation Draft")
        st.markdown(output if output else "(empty)")

    title = "Toastmasters Evaluation Draft"
    md_bytes = (output or "").encode("utf-8")
    html_doc = make_printable_html(title=title, body_markdown=output or "")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.download_button(
            "Download Markdown (.md)",
            data=md_bytes,
            file_name="evaluation_draft.md",
            mime="text/markdown",
        )
    with c2:
        st.download_button(
            "Download Print-HTML (.html)",
            data=html_doc.encode("utf-8"),
            file_name="evaluation_draft.html",
            mime="text/html",
        )
    with c3:
        st.caption("For PDF: open the HTML → Print → Save as PDF")

    st.write("---")

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Back to Evaluation"):
            set_page("evaluation")
            st.rerun()
    with colB:
        if st.button("Start New Evaluation"):
            st.session_state.clear()
            st.rerun()


# Safety fallback
else:
    set_page("intro")
    st.rerun()
