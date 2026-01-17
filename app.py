import time
import re
from pathlib import Path
import html

import streamlit as st

# --- CrewAI import (safe) ---
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

# ==================== EVALUATION CRITERIA (Ice Breaker) ====================
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
        4: "Delivers excellent speech with a topic that is well-supported by content of the speech.",
        3: "Speech is supported by the content of the speech.",
        2: "Speech contains content that supports the topic though some content may seem disconnected.",
        1: "Speech content is unrelated to the topic of the speech.",
    },
}

# Rubric rows (as per your sheet)
RUBRIC_DEF = [
    ("Clarity", "Spoken language is clear and is easily understood"),
    ("Vocal Variety", "Uses tone, speed, and volume as tools"),
    ("Eye Contact", "Effectively uses eye contact to engage audience"),
    ("Gestures", "Uses physical gestures effectively"),
    ("Audience Awareness", "Demonstrates awareness of audience engagement and needs"),
    ("Comfort Level", "Appears comfortable with the audience"),
    ("Interest", "Engages audience with interesting, well-constructed content"),
    ("Well Supported", "Topic is supported by the content of the speech"),
]


# ==================== SESSION STATE (router) ====================
if "page" not in st.session_state:
    # select -> loading -> evaluation -> draft_loading -> draft
    st.session_state.page = "select"

if "details" not in st.session_state:
    st.session_state.details = None

if "crewai_output" not in st.session_state:
    st.session_state.crewai_output = None

if "draft_md" not in st.session_state:
    st.session_state.draft_md = ""

if "draft_html" not in st.session_state:
    st.session_state.draft_html = ""

if "pending_generation" not in st.session_state:
    # Stores payload to generate draft on the next page.
    st.session_state.pending_generation = None

if "meeting" not in st.session_state:
    st.session_state.meeting = {"speaker": "", "evaluator": "", "date": None, "speech_title": ""}


# ==================== UI SETUP ====================
st.set_page_config(
    page_title="Toastmasters Evaluation Assistant T.E.A.",
    page_icon="☕",
    layout="centered",
)

st.markdown(
    """
    <style>
      textarea { background-color: #EAF0FF !important; }
      div[data-testid="stVerticalBlock"] > div { gap: 0.55rem; }
      /* Make the central project-details box feel less wide */
      .tea-narrow { max-width: 680px; margin: 0 auto; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================== HELPERS ====================
def find_logo_path():
    for p in LOGO_CANDIDATES:
        if p.exists():
            return p
    return None


def resolve_md_path(pathway_label: str) -> Path:
    expected = KB_DIR / PATHWAY_FILES[pathway_label]
    if expected.exists():
        return expected

    # If user renamed to Title.md (e.g., "Engaging Humor.md")
    alt_title = KB_DIR / f"{pathway_label}.md"
    if alt_title.exists():
        return alt_title

    # snake_case fallback
    alt_snake = KB_DIR / (pathway_label.lower().replace(" ", "_") + ".md")
    if alt_snake.exists():
        return alt_snake

    return expected


def extract_level_block(md_path: Path, level: str):
    if not md_path.exists():
        return None

    lines = md_path.read_text(encoding="utf-8").splitlines()
    level_header = f"## {level}"

    level_start = next(
        (i for i, line in enumerate(lines) if line.strip().lower() == level_header.lower()),
        None,
    )
    if level_start is None:
        return None

    level_end = next(
        (i for i in range(level_start + 1, len(lines)) if lines[i].strip().startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[level_start:level_end])


def extract_level_focus(level_block: str):
    m = re.search(r"\*\*Level focus.*?\*\*\s*:?\s*(.+)", level_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def get_projects_from_markdown(md_path: Path, level: str):
    level_block = extract_level_block(md_path, level)
    if not level_block:
        return []

    projects = re.findall(
        r"^###\s*Project:\s*(.+)\s*$",
        level_block,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    out, seen = [], set()
    for p in projects:
        p2 = p.strip()
        if p2 and p2.lower() not in seen:
            seen.add(p2.lower())
            out.append(p2)
    return out


def extract_project_block(level_block: str, project: str):
    lines = level_block.splitlines()
    project_header = f"### Project: {project}"

    proj_start = next(
        (i for i, line in enumerate(lines) if line.strip().lower() == project_header.lower()),
        None,
    )
    if proj_start is None:
        return None

    proj_end = next(
        (i for i in range(proj_start + 1, len(lines)) if lines[i].strip().startswith("### Project:")),
        len(lines),
    )
    return "\n".join(lines[proj_start:proj_end])


def extract_field(proj_block: str, field_name: str):
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*?\s*:?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def is_ice_breaker(project: str) -> bool:
    return project.strip().lower() == "ice breaker"


def render_full_ice_breaker_criteria():
    st.markdown("### Evaluation Criteria (Ice Breaker)")
    st.caption("Use these descriptions to guide your 1–5 ratings.")
    for name, _ in RUBRIC_DEF:
        st.markdown(f"**{name}**")
        mapping = SPEECH_EVALUATION_CRITERIA.get(name, {})
        for score in [5, 4, 3, 2, 1]:
            if score in mapping:
                st.markdown(f"- **{score}** — {mapping[score]}")
        st.markdown("---")


def render_rubric_table(rubric_def):
    """
    Official-sheet-like row layout:
      [Criteria] | [5 4 3 2 1] | [Comment box]
    Default rating = 3.
    """
    rubric_items = []

    with st.container(border=True):
        h1, h2, h3 = st.columns([2.2, 3.2, 3.6], vertical_alignment="center")
        with h1:
            st.markdown("**Criteria**")
        with h2:
            st.markdown("**Rating (5 → 1)**")
            st.caption("5=Exemplary • 4=Excels • 3=Accomplished • 2=Emerging • 1=Developing")
        with h3:
            st.markdown("**Comment**")

        st.markdown("---")

        for name, desc in rubric_def:
            c1, c2, c3 = st.columns([2.2, 3.2, 3.6], vertical_alignment="center")

            with c1:
                st.markdown(f"**{name}**")
                st.caption(desc)

            with c2:
                rating = st.radio(
                    label=f"{name} rating",
                    options=[5, 4, 3, 2, 1],
                    index=2,  # ✅ default = 3
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"rubric_rating_{name}",
                )

            with c3:
                comment = st.text_area(
                    label=f"{name} comment",
                    height=70,
                    placeholder="Optional short comment…",
                    label_visibility="collapsed",
                    key=f"rubric_comment_{name}",
                )

            rubric_items.append({"name": name, "rating": int(rating), "comment": comment})

            st.markdown(
                "<hr style='margin:0.35rem 0; border:0; border-top:1px solid #eee;'>",
                unsafe_allow_html=True,
            )

    return rubric_items


def build_rubric_summary(rubric_items):
    strengths, improvements = [], []
    for item in rubric_items:
        name = item["name"]
        rating = int(item["rating"])
        comment = (item.get("comment") or "").strip()

        line = f"- {name} ({rating}/5): {comment}" if comment else f"- {name} ({rating}/5)"
        if rating >= 4:
            strengths.append(line)
        else:
            improvements.append(line)

    strengths_text = "\n".join(strengths) if strengths else "- (none selected)"
    improvements_text = "\n".join(improvements) if improvements else "- (none selected)"
    return strengths_text, improvements_text


def compute_total_score(rubric_items):
    return sum(int(x.get("rating", 0)) for x in rubric_items)


def overall_band(total_score):
    # For 8 criteria (max 40). If you add/remove criteria later, you can adjust these thresholds.
    if total_score >= 36:
        return "Outstanding (Exceptional/Superior)", "success"
    if total_score >= 28:
        return "Proficient (Expertise/Mastery)", "info"
    if total_score >= 20:
        return " Competent (Meets Standard)", "warning"
    return "Needs Improvement (Below Standard)", "error"


def build_selected_criteria_text(project: str, rubric_items):
    if not is_ice_breaker(project):
        return ""
    lines = ["Evaluation criteria meaning (Ice Breaker):"]
    for item in rubric_items:
        name = item["name"]
        rating = int(item["rating"])
        desc = SPEECH_EVALUATION_CRITERIA.get(name, {}).get(rating, "")
        if desc:
            lines.append(f"- {name} {rating}/5: {desc}")
        else:
            lines.append(f"- {name} {rating}/5")
    return "\n".join(lines)


def build_export_html(
    title: str,
    meeting: dict,
    selection: dict,
    draft_md: str,
) -> str:
    """Create a clean, print-to-PDF-friendly HTML file."""

    # Very small markdown -> HTML (safe fallback)
    try:
        import markdown as md  # type: ignore

        draft_html = md.markdown(draft_md, extensions=["fenced_code", "tables"])
    except Exception:
        draft_html = f"<pre style='white-space:pre-wrap'>{html.escape(draft_md)}</pre>"

    def row(k, v):
        v = "" if v is None else str(v)
        return f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>"

    meeting_rows = "".join(
        [
            row("Speaker", meeting.get("speaker_name")),
            row("Evaluator", meeting.get("evaluator_name")),
            row("Date", meeting.get("meeting_date")),
            row("Speech Title", meeting.get("speech_title")),
        ]
    )
    selection_rows = "".join(
        [
            row("Pathway", selection.get("pathway")),
            row("Level", selection.get("level")),
            row("Project", selection.get("project")),
            row("Speech Length", selection.get("speech_len")),
        ]
    )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; margin: 32px; color:#111; }}
    h1 {{ margin: 0 0 6px 0; font-size: 28px; }}
    .subtitle {{ color:#555; margin-bottom: 18px; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 18px 0 22px 0; }}
    .card {{ border:1px solid #e6e6e6; border-radius: 12px; padding: 14px 16px; }}
    table {{ width:100%; border-collapse: collapse; }}
    th {{ text-align:left; padding:6px 0; width: 32%; color:#444; font-weight:600; vertical-align: top; }}
    td {{ padding:6px 0; }}
    hr {{ border:0; border-top:1px solid #eee; margin: 20px 0; }}
    .draft {{ line-height: 1.55; }}
    @media print {{ body {{ margin: 16mm; }} .card {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class=\"subtitle\">Generated by Toastmasters Evaluation Assistant (T.E.A.)</div>

  <div class=\"grid\">
    <div class=\"card\">
      <h2 style=\"margin:0 0 8px 0; font-size:18px\">Meeting Details</h2>
      <table>{meeting_rows}</table>
    </div>
    <div class=\"card\">
      <h2 style=\"margin:0 0 8px 0; font-size:18px\">Project Selection</h2>
      <table>{selection_rows}</table>
    </div>
  </div>

  <hr />
  <h2 style=\"margin:0 0 10px 0\">Evaluation Draft</h2>
  <div class=\"draft\">{draft_html}</div>
</body>
</html>"""


def render_header():
    logo_path = find_logo_path()
    h1, h2 = st.columns([1, 5], vertical_alignment="center")
    with h1:
        if logo_path:
            st.image(str(logo_path), use_container_width=True)
    with h2:
        st.markdown("# Toastmasters Evaluation Assistant T.E.A.")
        st.caption(
            "Objective of T.E.A. is to help speech evaluators turn rubric ratings + rough notes into a structured, "
            "project-aligned evaluation draft, by retrieving the selected Pathways project purpose/level focus "
            "from a local knowledge base and using CrewAI to generate an editable evaluation."
        )
        st.caption("NYP ITI123 Application Development Project by Zhu Qihui, Oscar 9801937V")


def render_step_indicator():
    page = st.session_state.get("page", "select")
    steps = [
        ("Step 1/4", "Select Project Details", "select"),
        ("Step 2/4", "Load Project", "loading"),
        ("Step 3/4", "Evaluation Form", "evaluation"),
        ("Step 4/4", "Draft & Export", "draft_loading"),
    ]
    page_to_idx = {
        "select": 0,
        "loading": 1,
        "evaluation": 2,
        "draft_loading": 3,
        "draft": 3,
    }
    idx = page_to_idx.get(page, 0)

    a, b, c, d = st.columns(4)
    cols = [a, b, c, d]
    for i, (label, name, _) in enumerate(steps):
        with cols[i]:
            if i == idx:
                st.markdown(f"**✅ {label}**  \n{name}")
            elif i < idx:
                st.markdown(f"**✔ {label}**  \n{name}")
            else:
                st.markdown(f"**◻ {label}**  \n{name}")

    st.progress((idx + 1) / 4)


# ==================== PAGE 1: SELECT ====================
if st.session_state.page == "select":
    render_header()
    render_step_indicator()
    st.divider()

    st.subheader("Chapter Meeting Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        speaker_name = st.text_input(
            "Speaker Name",
            value=st.session_state.meeting.get("speaker", ""),
            placeholder="e.g., Oscar Zhu",
        )
    with c2:
        evaluator_name = st.text_input(
            "Evaluator Name",
            value=st.session_state.meeting.get("evaluator", ""),
            placeholder="e.g., Lee Ching Yuh",
        )
    with c3:
        meeting_date = st.date_input("Date of Chapter Meeting", value=st.session_state.meeting.get("date"))

    speech_title = st.text_input(
        "Speech Title",
        value=st.session_state.meeting.get("speech_title", ""),
        placeholder="e.g., Living with Dignity or Charity",
    )

    st.session_state.meeting = {
        "speaker": speaker_name,
        "evaluator": evaluator_name,
        "date": meeting_date,
        "speech_title": speech_title,
    }

    st.divider()

    pathway = st.selectbox("Select Pathway", list(PATHWAY_FILES.keys()), key="pathway_sel")
    level = st.selectbox("Select Level", LEVELS, key="level_sel")

    md_path = resolve_md_path(pathway)
    if not md_path.exists():
        st.error(f"Markdown file not found for '{pathway}'. Expected at: {md_path}")
        st.stop()

    project_options = get_projects_from_markdown(md_path, level)
    if not project_options:
        st.warning(f"No projects found for **{level}** in **{md_path.name}**.")
        st.info("Fix: add headings like `### Project: <Project Name>` under `## Level X`.")
        st.stop()

    project = st.selectbox("Select Project", project_options, key="project_sel")

    b1, b2 = st.columns([1, 1])
    with b1:
        get_details = st.button("Get Details")
    with b2:
        clear = st.button("Clear")

    if clear:
        st.session_state.details = None
        st.session_state.crewai_output = None
        st.session_state.page = "select"
        st.rerun()

    if get_details:
        level_block = extract_level_block(md_path, level)
        if not level_block:
            st.error(f"❌ Level '{level}' not found in {md_path.name}.")
            st.info("Fix: Add heading like `## Level 2` into the markdown file.")
            st.stop()

        proj_block = extract_project_block(level_block, project)
        if not proj_block:
            st.error(
                f"❌ '{project}' is not found under **{level}** in **{md_path.name}**.\n\n"
                "✅ Please select the correct pathway OR add this project into the pathway markdown file."
            )
            available = re.findall(r"^###\s*Project:\s*(.+)\s*$", level_block, flags=re.IGNORECASE | re.MULTILINE)
            if available:
                st.caption("Projects currently found in this pathway + level:")
                st.write(available)
            st.stop()

        level_focus = extract_level_focus(level_block) or "Not found"
        purpose = extract_field(proj_block, "Purpose") or "Not found"
        speech_len = (
            extract_field(proj_block, "Speech length (optional)")
            or extract_field(proj_block, "Speech length")
            or "Not found"
        )

        st.session_state.details = {
            "pathway": pathway,
            "level": level,
            "project": project,
            "level_focus": level_focus,
            "purpose": purpose,
            "speech_len": speech_len,
            "md_path": str(md_path),
        }
        st.session_state.crewai_output = None

        st.session_state.page = "loading"
        st.rerun()

    st.caption(f"Using file: {md_path}")


# ==================== PAGE 4: Draft Loading ====================
if st.session_state.page == "draft_loading":
    render_header()
    render_step_indicator()

    pending = st.session_state.get("pending_generation") or {}
    if not pending:
        st.warning("No pending draft request found. Please generate from the Evaluation Form.")
        if st.button("⬅ Back to Evaluation Form"):
            st.session_state.page = "evaluation"
            st.rerun()
        st.stop()

    st.subheader("Generating evaluation draft")
    st.caption("Please wait… preparing your draft (minimum 3 seconds).")

    # Minimum visible loading time
    p = st.progress(0)
    for i in range(30):
        p.progress(int((i + 1) / 30 * 100))
        time.sleep(0.1)

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
                total_score=pending.get("total_score"),
                score_label=pending.get("score_label", ""),
            )

    st.session_state.crewai_output = output
    st.session_state.draft_md = output

    meeting = pending.get("meeting", {})
    selection = {
        "pathway": pending.get("pathway"),
        "level": pending.get("level"),
        "project": pending.get("project"),
        "speech_len": pending.get("speech_len"),
    }
    st.session_state.draft_html = build_export_html(
        title="Toastmasters Evaluation Draft",
        meeting=meeting,
        selection=selection,
        draft_md=output,
    )

    st.session_state.page = "draft"
    st.rerun()


# ==================== PAGE 5: Draft + Export ====================
if st.session_state.page == "draft":
    render_header()
    render_step_indicator()

    st.subheader("Evaluation draft (editable)")
    draft_default = st.session_state.get("draft_md") or ""
    edited = st.text_area(
        "You can edit the draft below before exporting:",
        value=draft_default,
        height=520,
        key="draft_editor",
    )

    # Build filenames
    ts = time.strftime("%Y%m%d_%H%M%S")
    md_name = f"tea_evaluation_draft_{ts}.md"
    html_name = f"tea_evaluation_draft_{ts}.html"

    st.markdown("---")
    st.subheader("Export")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ Download Markdown",
            data=edited.encode("utf-8"),
            file_name=md_name,
            mime="text/markdown",
            use_container_width=True,
        )
    with c2:
        # Rebuild HTML using the edited version (for PDF-print friendly output)
        meeting = (st.session_state.get("pending_generation") or {}).get("meeting", {})
        selection = {
            "pathway": (st.session_state.get("pending_generation") or {}).get("pathway"),
            "level": (st.session_state.get("pending_generation") or {}).get("level"),
            "project": (st.session_state.get("pending_generation") or {}).get("project"),
            "speech_len": (st.session_state.get("pending_generation") or {}).get("speech_len"),
        }
        html_out = build_export_html(
            title="Toastmasters Evaluation Draft",
            meeting=meeting,
            selection=selection,
            draft_md=edited,
        )
        st.download_button(
            "⬇️ Download HTML (print to PDF)",
            data=html_out.encode("utf-8"),
            file_name=html_name,
            mime="text/html",
            use_container_width=True,
        )

    st.caption(
        "PDF tip: open the downloaded HTML in Chrome/Edge, then use Print → Save as PDF. "
        "(This keeps formatting cleaner than copying from the app.)"
    )

    st.markdown("---")
    back1, back2 = st.columns(2)
    with back1:
        if st.button("⬅ Back to Evaluation Form"):
            st.session_state.page = "evaluation"
            st.rerun()
    with back2:
        if st.button("🏠 Start Over"):
            st.session_state.page = "select"
            st.rerun()
    st.stop()


# ==================== PAGE 2: LOADING ====================
if st.session_state.page == "loading":
    render_header()
    render_step_indicator()
    st.divider()

    st.subheader("Loading project details…")
    st.caption("Please wait while we prepare the evaluation form.")
    bar = st.progress(0)

    # >= 3 seconds
    for i in range(101):
        bar.progress(i)
        time.sleep(0.03)

    st.session_state.page = "evaluation"
    st.rerun()


# ==================== PAGE 3: EVALUATION ====================
if st.session_state.page == "evaluation":
    if not st.session_state.details:
        st.session_state.page = "select"
        st.rerun()

    render_header()
    render_step_indicator()
    st.divider()

    top1, top2, top3 = st.columns([1, 1, 2])
    with top1:
        if st.button("⬅ Back"):
            st.session_state.page = "select"
            st.rerun()
    with top2:
        if st.button("🧹 Clear All"):
            st.session_state.details = None
            st.session_state.crewai_output = None
            st.session_state.page = "select"
            st.rerun()

    d = st.session_state.details
    meeting = st.session_state.meeting
    meeting_date = meeting.get("date")
    meeting_date_str = str(meeting_date) if meeting_date else "N/A"

    meeting_speech_title = (meeting.get("speech_title") or "").strip()

    st.subheader("Chapter Meeting Details")
    st.markdown('<div class="tea-narrow">', unsafe_allow_html=True)
    with st.container(border=True):
        a1, a2, a3 = st.columns([1.2, 1.2, 1.6])
        with a1:
            st.markdown('**Speaker**')
            st.write(meeting.get('speaker') or 'N/A')
        with a2:
            st.markdown('**Evaluator**')
            st.write(meeting.get('evaluator') or 'N/A')
        with a3:
            st.markdown('**Date**')
            st.write(meeting_date_str)

        st.markdown('---')
        st.markdown('**Speech Title**')
        st.write(meeting_speech_title or 'N/A')
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ---- Project Details (narrow centered box) ----
    st.subheader("Project Details")
    st.markdown('<div class="tea-narrow">', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Pathway**")
        st.write(d["pathway"])

        st.markdown("---")
        st.markdown("**Level focus**")
        st.write(d["level_focus"])

        st.markdown("---")
        st.markdown("**Purpose**")
        st.write(d["purpose"])

        st.markdown("---")
        st.markdown("**Speech length**")
        st.write(d["speech_len"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ---- Rubrics ----
    st.subheader("Rubric Ratings (1–5)")
    st.caption("Rule: ratings 4–5 → Strengths, ratings 1–3 → Areas for improvement.")

    if is_ice_breaker(d["project"]):
        with st.expander("View Evaluation Criteria (Ice Breaker)"):
            render_full_ice_breaker_criteria()

    rubric_items = render_rubric_table(RUBRIC_DEF)

    # ✅ Total score + legend
    total_score = compute_total_score(rubric_items)
    max_score = len(rubric_items) * 5

    st.subheader("Speaker's Competency Total Accumulated Score")
    cA, cB = st.columns([1.2, 2.8], vertical_alignment="center")
    with cA:
        st.metric("Total Score", f"{total_score} / {max_score}")
    with cB:
        st.progress(total_score / max_score if max_score else 0)

    st.markdown("**Legend (Total Score Range)**")
    st.markdown(
        """
- **36-40** → **Outstanding (Exceptional/Superior)**
- **28–35** → **Proficient (Expertise/Mastery)**
- **20–27** → **Competent (Meets Standard)**
- **8–19** → **Needs Improvement (Below Standard)**
"""
    )

    label, style = overall_band(total_score)
    if style == "success":
        st.success(f"Overall Result: {label}")
    elif style == "info":
        st.info(f"Overall Result: {label}")
    elif style == "warning":
        st.warning(f"Overall Result: {label}")
    else:
        st.error(f"Overall Result: {label}")

    # Strengths / Improvements (lists)
    strengths_text, improvements_text = build_rubric_summary(rubric_items)

    st.divider()

    s1, s2 = st.columns(2)
    with s1:
        st.markdown("### Strengths (4–5)")
        st.markdown(strengths_text)
    with s2:
        st.markdown("### Areas for Improvement (1–3)")
        st.markdown(improvements_text)

    st.divider()

    # ---- General comments ----
    st.subheader("General Comments - By Project Speech Evaluator")
    st.caption("Tip: You can leave some boxes blank. At least one note/comment is needed before generating.")

    t1, t2 = st.columns(2)
    with t1:
        excelled = st.text_area("✅ You excelled at:", height=140)
    with t2:
        work_on = st.text_area("🔧 You may want to work on:", height=140)
    challenge = st.text_area("🎯 To challenge yourself:", height=140)

    selected_criteria_text = build_selected_criteria_text(d["project"], rubric_items)

    notes_payload = f"""
Meeting details:
- Speaker: {meeting.get("speaker") or "N/A"}
- Evaluator: {meeting.get("evaluator") or "N/A"}
- Date: {meeting_date_str}
- Speech title: {meeting.get('speech_title') or 'N/A'}

Selected project context:
- Pathway: {d["pathway"]}
- Level: {d["level"]}
- Project: {d["project"]}
- Speech length: {d["speech_len"]}

Level focus:
{d["level_focus"]}

Purpose:
{d["purpose"]}

Total score:
- {total_score}/{max_score} ({label})

{selected_criteria_text}

Rubric summary (auto):
Strengths (ratings 4–5):
{strengths_text}

Areas for improvement (ratings 1–3):
{improvements_text}

General comments:
You excelled at:
{excelled}

You may want to work on:
{work_on}

To challenge yourself:
{challenge}
""".strip()

    if st.button("Generate Evaluation Draft (CrewAI)"):
        if run_crewai_eval is None:
            st.error("CrewAI module failed to import.")
            st.code(CREWAI_IMPORT_ERROR)
        else:
            has_general = (excelled.strip() or work_on.strip() or challenge.strip())
            has_any_rubric_comment = any((x.get("comment") or "").strip() for x in rubric_items)
            if not has_general and not has_any_rubric_comment:
                st.warning("Please add at least one rubric comment OR fill one general comment box before generating.")
            else:
                # Save payload and navigate to a fresh Draft page.
                # Everything Step 4 needs (use `.get()` when reading to avoid KeyError)
                st.session_state.pending_generation = {
                    "notes_payload": notes_payload,
                    "pathway": d.get("pathway", ""),
                    "level": d.get("level", ""),
                    "project": d.get("project", ""),
                    "level_focus": d.get("level_focus", ""),
                    "purpose": d.get("purpose", ""),
                    "speech_len": d.get("speech_len", ""),
                    # Extra context to strengthen the CrewAI prompt
                    "criteria_text": selected_criteria_text,
                    "total_score": total_score,
                    "max_score": max_score,
                    "score_band": label,
                }
                st.session_state.crewai_output = None
                st.session_state.page = "draft_loading"
                st.rerun()

    st.caption(f"Using file: {d.get('md_path', '')}")


# ==================== PAGE 4: Draft Loading ====================
if st.session_state.page == "draft_loading":
    render_header()
    render_step_indicator()

    pending = st.session_state.get("pending_generation") or {}
    if not pending:
        st.warning("No pending draft request found. Please generate from the Evaluation Form first.")
        if st.button("⬅ Back to Evaluation Form"):
            st.session_state.page = "evaluation"
            st.rerun()
        st.stop()

    st.subheader("Generating Evaluation Draft")
    st.caption("Please wait… this will show the draft on a fresh page.")

    # Minimum 3-second progress bar (always)
    progress = st.progress(0)
    for i in range(30):
        progress.progress((i + 1) / 30)
        time.sleep(0.1)

    # Then run CrewAI (may take longer)
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
            )

    st.session_state.crewai_output = output
    st.session_state.draft_md = output
    st.session_state.page = "draft"
    st.rerun()


# ==================== PAGE 5: Draft & Export ====================
if st.session_state.page == "draft":
    render_header()
    render_step_indicator()

    draft_md = st.session_state.get("draft_md") or st.session_state.get("crewai_output") or ""
    pending = st.session_state.get("pending_generation") or {}

    st.subheader("Evaluation Draft (Editable)")
    st.caption("Edit the draft if you want. Then export using the buttons below (print-to-PDF friendly).")

    edited = st.text_area(
        "Draft output",
        value=draft_md,
        height=520,
        key="draft_editor",
    )

    st.divider()
    st.subheader("Export")

    # Build a clean HTML file for printing to PDF
    meeting = st.session_state.get("meeting", {})
    selection = {
        "pathway": pending.get("pathway", ""),
        "level": pending.get("level", ""),
        "project": pending.get("project", ""),
        "speech_len": pending.get("speech_len", ""),
    }

    html_doc = build_export_html(
        title="Toastmasters Evaluation Draft",
        meeting=meeting,
        selection=selection,
        draft_md=edited,
    )

    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"toastmasters_evaluation_{ts}"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Download Draft (.md)",
            data=edited.encode("utf-8"),
            file_name=f"{base}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Download Print-to-PDF HTML (.html)",
            data=html_doc.encode("utf-8"),
            file_name=f"{base}.html",
            mime="text/html",
            use_container_width=True,
        )
    with c3:
        st.download_button(
            "Download Draft (.txt)",
            data=edited.encode("utf-8"),
            file_name=f"{base}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.info(
        "For PDF: download the HTML, open it in Chrome, then use **Print → Save as PDF**. "
        "(The HTML is styled to be print-friendly.)"
    )

    st.divider()
    b1, b2 = st.columns(2)
    with b1:
        if st.button("⬅ Back to Evaluation Form", use_container_width=True):
            st.session_state.page = "evaluation"
            st.rerun()
    with b2:
        if st.button("Start New Evaluation", use_container_width=True):
            for k in [
                "details",
                "meeting",
                "ratings",
                "rubric_comments",
                "crewai_output",
                "draft_md",
                "pending_generation",
                "draft_editor",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state.page = "select"
            st.rerun()


