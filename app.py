import time
import re
from pathlib import Path
import html
from io import BytesIO

import streamlit as st

# --- Optional PDF export (ReportLab) ---
# NOTE: For best formatting, use the HTML export and Print → Save as PDF.
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    _PDF_OK = True
    _PDF_IMPORT_ERROR = ""
except Exception as _e:
    A4 = None  # type: ignore
    canvas = None  # type: ignore
    cm = None  # type: ignore
    _PDF_OK = False
    _PDF_IMPORT_ERROR = str(_e)


# --- CrewAI import (safe) ---
# Prefer updated module name; fall back to original.
CREWAI_IMPORT_ERROR = ""
try:
    from crewai_eval_updated import run_crewai_eval, purpose_alignment_summary  # type: ignore
except Exception:
    try:
        from crewai_eval import run_crewai_eval, purpose_alignment_summary  # type: ignore
    except Exception as e:
        run_crewai_eval = None
        purpose_alignment_summary = None
        CREWAI_IMPORT_ERROR = str(e)


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

# Rubric rows (Ice Breaker)
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


# ==================== SESSION STATE ====================
if "page" not in st.session_state:
    st.session_state.page = "select"  # select -> loading -> evaluation -> draft_loading -> draft

if "details" not in st.session_state:
    st.session_state.details = None

if "draft_md" not in st.session_state:
    st.session_state.draft_md = ""

if "pending_generation" not in st.session_state:
    st.session_state.pending_generation = None

if "meeting" not in st.session_state:
    st.session_state.meeting = {"speaker": "", "evaluator": "", "date": None, "speech_title": ""}


# ==================== UI SETUP ====================
st.set_page_config(
    page_title="Toastmasters Evaluation Assistant (T.E.A.)",
    page_icon="☕",
    layout="centered",
)

st.markdown(
    """
    <style>
      textarea { background-color: #EAF0FF !important; }
      div[data-testid="stVerticalBlock"] > div { gap: 0.55rem; }
      .tea-narrow { max-width: 720px; margin: 0 auto; }
      /* Make radios tighter like a paper form */
      div[role="radiogroup"] label { padding-right: 0.25rem; }
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

    alt_title = KB_DIR / f"{pathway_label}.md"
    if alt_title.exists():
        return alt_title

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
    Form-like row layout:
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
                    index=2,
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


def overall_band(total_score: int):
    # For 8 criteria (max 40). If you add/remove criteria later, adjust thresholds.
    if total_score >= 36:
        return "Outstanding (Exceptional/Superior)", "success"
    if total_score >= 28:
        return "Proficient (Expertise/Mastery)", "info"
    if total_score >= 20:
        return "Competent (Meets Standard)", "warning"
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


def _split_md_sections(md_text: str) -> dict:
    """Split draft markdown into named sections based on required headings."""
    md = (md_text or "").strip()
    if not md:
        return {}

    # Normalize headings (## Heading)
    sections = {}
    current = None
    buf = []

    def commit():
        nonlocal current, buf
        if current is not None:
            sections[current] = "\n".join(buf).strip()
        buf = []

    for ln in md.splitlines():
        m = re.match(r"^\s*##\s+(.+?)\s*$", ln)
        if m:
            commit()
            current = m.group(1).strip()
            continue
        buf.append(ln)

    commit()
    return sections


def _extract_alignment_checks(md_text: str) -> tuple[str, dict[str, bool], list[str]]:
    """Extract Purpose Alignment summary + checklist + reason bullets.

    Anti-hallucination logic:
    - If Evidence lines are missing, force all checklist items to False.
    - If Evidence lines contain "Insufficient evidence...", force the related checklist items to False
      even if the model checked them.
    """
    checks = {
        "Purpose clearly addressed": False,
        "Level focus demonstrated": False,
        "Feedback linked to evaluation criteria": False,
        "Balanced commendations + improvements": False,
        "Actionable next step provided": False,
    }
    reasons: list[str] = []
    summary = ""

    sections = _split_md_sections(md_text)
    block = sections.get("Purpose Alignment") or sections.get("Purpose alignment") or ""
    if not block:
        return summary, checks, reasons

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]

    # Summary: first 1–2 non-checklist lines
    collected = []
    for ln in lines:
        if re.match(r"^\-\s*\[(x| )\]\s+", ln, flags=re.IGNORECASE):
            break
        if ln.lower().startswith("evidence:"):
            continue
        if ln.startswith("-") and not ln.lower().startswith("- alignment claim"):
            continue
        collected.append(ln)
        if len(collected) >= 2:
            break
    summary = " ".join(collected).strip()

    # Parse checklist (if present)
    for ln in lines:
        mm = re.match(r"^\-\s*\[(x| )\]\s*(.+?)\s*$", ln, flags=re.IGNORECASE)
        if not mm:
            continue
        checked = mm.group(1).lower() == "x"
        label = mm.group(2).strip().lower()
        for k in list(checks.keys()):
            kk = k.lower()
            if kk in label or label in kk:
                checks[k] = checked

    # Reasons: bullets (best effort)
    for ln in lines:
        if re.match(r"^\-\s*\[(x| )\]\s+", ln, flags=re.IGNORECASE):
            continue
        if ln.startswith("-") and not ln.lower().startswith("- alignment claim"):
            reasons.append(ln.lstrip("-").strip())
    reasons = [r for r in reasons if r and len(r) <= 180][:3]

    # --- Evidence binding enforcement ---
    evidence_lines = [ln for ln in lines if ln.lower().startswith("evidence:")]
    if not evidence_lines:
        for k in checks:
            checks[k] = False
        return summary, checks, reasons

    insufficient = any("insufficient evidence" in ln.lower() for ln in evidence_lines)
    if insufficient:
        checks["Purpose clearly addressed"] = False
        checks["Level focus demonstrated"] = False

    has_rubric_hint = any(("rubric" in ln.lower() or "/5" in ln or "criteria" in ln.lower()) for ln in evidence_lines)
    if not has_rubric_hint:
        checks["Feedback linked to evaluation criteria"] = False

    return summary, checks, reasons


    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    # Summary: first 1–2 non-checklist lines
    collected = []
    for ln in lines:
        if re.match(r"^-\s*\[(x| )\]\s+", ln, flags=re.IGNORECASE):
            break
        if ln.startswith("-"):
            continue
        collected.append(ln)
        if len(collected) >= 2:
            break
    summary = " ".join(collected).strip()

    # Checklist
    for ln in lines:
        mm = re.match(r"^-\s*\[(x| )\]\s*(.+?)\s*$", ln, flags=re.IGNORECASE)
        if not mm:
            continue
        checked = mm.group(1).lower() == "x"
        label = mm.group(2).strip().lower()
        for k in list(checks.keys()):
            kk = k.lower()
            if kk in label or label in kk:
                checks[k] = checked

    # Reasons: bullets after checklist lines (best effort)
    for ln in lines:
        if re.match(r"^-\s*\[(x| )\]\s+", ln, flags=re.IGNORECASE):
            continue
        if ln.startswith("-") and not re.match(r"^-\s*\[(x| )\]\s+", ln, flags=re.IGNORECASE):
            reasons.append(ln.lstrip("-").strip())

    reasons = [r for r in reasons if r and len(r) <= 180][:3]
    return summary, checks, reasons


def build_export_html_form(
    title: str,
    meeting: dict,
    selection: dict,
    draft_md: str,
) -> str:
    """Create a print-to-PDF-friendly HTML styled like the official Toastmasters evaluation form."""
    # Markdown -> HTML
    try:
        import markdown as md  # type: ignore

        md_html = md.markdown(draft_md or "", extensions=["fenced_code"])
    except Exception:
        md_html = f"<pre style='white-space:pre-wrap'>{html.escape(draft_md or '')}</pre>"

    # Parse structured sections for form boxes
    sections = _split_md_sections(draft_md or "")
    opening = sections.get("Opening", "").strip()
    strengths = sections.get("Strengths", "").strip()
    recs = sections.get("Recommendations", "").strip()
    challenge = sections.get("One Challenge", "").strip()

    align_summary, align_checks, align_reasons = _extract_alignment_checks(draft_md or "")

    def esc(x):
        return html.escape("" if x is None else str(x))

    def row(k, v):
        return f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>"

    meeting_rows = "".join(
        [
            row("Speaker", meeting.get("speaker", "")),
            row("Evaluator", meeting.get("evaluator", "")),
            row("Date", meeting.get("meeting_date", "")),
            row("Speech Title", meeting.get("speech_title", "")),
        ]
    )
    selection_rows = "".join(
        [
            row("Pathway", selection.get("pathway", "")),
            row("Level", selection.get("level", "")),
            row("Project", selection.get("project", "")),
            row("Target Speech Length", selection.get("speech_len", "")),
            row("Project Purpose", selection.get("purpose", "")),
            row("Level Focus", selection.get("level_focus", "")),
        ]
    )

    # Render checklist as form-style ticks
    def checkbox_line(label: str, checked: bool) -> str:
        box = "☑" if checked else "☐"
        return f"<div class='chk'><span class='box'>{box}</span><span>{esc(label)}</span></div>"

    checklist_html = "".join(checkbox_line(k, v) for k, v in align_checks.items())

    reasons_html = ""
    if align_reasons:
        reasons_html = "<ul class='tight'>" + "".join(f"<li>{esc(r)}</li>" for r in align_reasons) + "</ul>"

    # Helper to show plain text in a box (keep evaluator handwriting feel)
    def box_text(text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "<div class='lines'></div>"
        # Convert simple markdown bullets to HTML list inside box for readability
        try:
            import markdown as md  # type: ignore
            return md.markdown(text, extensions=["fenced_code"])
        except Exception:
            return f"<pre style='white-space:pre-wrap; margin:0'>{esc(text)}</pre>"

    opening_html = box_text(opening)
    strengths_html = box_text(strengths)
    recs_html = box_text(recs)
    challenge_html = box_text(challenge)

    # Signature lines
    sig_table = f"""
    <table class="sig">
      <tr>
        <th>Evaluator Signature</th>
        <td class="sigline"></td>
      </tr>
      <tr>
        <th>Date</th>
        <td class="sigline"></td>
      </tr>
    </table>
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{esc(title)}</title>
  <style>
    @page {{ size: A4; margin: 16mm; }}
    body {{
      font-family: Arial, Helvetica, sans-serif;
      font-size: 11pt;
      color: #000;
    }}
    h1 {{
      font-size: 16pt;
      margin: 0 0 4mm 0;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}
    .sub {{
      font-size: 10pt;
      margin: 0 0 6mm 0;
    }}
    .section {{
      border: 1px solid #000;
      padding: 8px 10px;
      margin-bottom: 4mm;
      break-inside: avoid;
    }}
    .section h2 {{
      font-size: 11pt;
      margin: 0 0 2mm 0;
      text-transform: uppercase;
      letter-spacing: 0.2px;
    }}
    table.meta {{
      width: 100%;
      border-collapse: collapse;
      font-size: 10.5pt;
    }}
    table.meta th {{
      text-align: left;
      padding: 2mm 2mm 2mm 0;
      width: 28%;
      vertical-align: top;
      font-weight: bold;
    }}
    table.meta td {{
      padding: 2mm 0;
      vertical-align: top;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4mm;
    }}
    .lines {{
      height: 44mm;
      background-image: linear-gradient(to bottom, transparent 0, transparent 19px, #d0d0d0 20px);
      background-size: 100% 20px;
      background-repeat: repeat-y;
    }}
    .tight ul, ul.tight {{
      margin: 0;
      padding-left: 18px;
    }}
    .chk {{
      display: flex;
      align-items: flex-start;
      gap: 6px;
      margin: 1.2mm 0;
      font-size: 10.5pt;
    }}
    .box {{
      width: 16px;
      display: inline-block;
    }}
    .sig {{
      width: 100%;
      border-collapse: collapse;
      font-size: 10.5pt;
    }}
    .sig th {{
      text-align:left;
      width: 28%;
      padding: 2mm 2mm 2mm 0;
      font-weight: bold;
    }}
    .sigline {{
      border-bottom: 1px solid #000;
      height: 8mm;
    }}
    .footer-note {{
      font-size: 9.5pt;
      margin-top: 2mm;
    }}
    @media print {{
      a {{ color: #000; text-decoration: none; }}
    }}
  </style>
</head>
<body>
  <h1>{esc(title)}</h1>
  <div class="sub">Toastmasters Evaluation Assistant (T.E.A.) — Meeting-ready export layout</div>

  <div class="section">
    <h2>Meeting Information</h2>
    <table class="meta">{meeting_rows}</table>
  </div>

  <div class="section">
    <h2>Pathways Project & Objectives</h2>
    <table class="meta">{selection_rows}</table>
  </div>

  <div class="section">
    <h2>Opening</h2>
    {opening_html}
  </div>

  <div class="two-col">
    <div class="section">
      <h2>What the Speaker Did Well</h2>
      {strengths_html}
    </div>
    <div class="section">
      <h2>Recommendations for Improvement</h2>
      {recs_html}
    </div>
  </div>

  <div class="section">
    <h2>One Challenge (Action Step)</h2>
    {challenge_html}
  </div>

  <div class="section">
    <h2>Evaluator Alignment Checklist</h2>
    <div class="footer-note">{esc(align_summary) if align_summary else ""}</div>
    {checklist_html}
    {reasons_html}
  </div>

  <div class="section">
    <h2>Sign-off</h2>
    {sig_table}
  </div>

  <div class="footer-note">Tip: For the cleanest PDF, open this HTML in Chrome/Edge → Print → Save as PDF.</div>

  <!-- Full draft (optional appendix for completeness) -->
  <div class="section">
    <h2>Appendix: Full Draft (for editing/record)</h2>
    {md_html}
  </div>
</body>
</html>"""


def make_pdf_bytes_simple(title: str, body_text: str) -> bytes:
    """Simple A4 PDF (plain text) for download (fallback)."""
    if canvas is None or A4 is None or cm is None:
        return b""

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    x = 2 * cm
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 13)
    c.drawString(x, y, title)
    y -= 0.9 * cm
    c.setFont("Helvetica", 10)

    max_width = width - 4 * cm
    line_height = 0.55 * cm

    def new_page():
        nonlocal y
        c.showPage()
        c.setFont("Helvetica", 10)
        y = height - 2 * cm

    for para in (body_text or "").split("\n"):
        words = para.split() if para.strip() else []
        if not words:
            y -= line_height
            if y < 2 * cm:
                new_page()
            continue

        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, "Helvetica", 10) <= max_width:
                line = test
            else:
                c.drawString(x, y, line)
                y -= line_height
                if y < 2 * cm:
                    new_page()
                line = w

        if line:
            c.drawString(x, y, line)
            y -= line_height
            if y < 2 * cm:
                new_page()

    c.save()
    return buf.getvalue()


def render_header():
    logo_path = find_logo_path()
    h1, h2 = st.columns([1, 5], vertical_alignment="center")
    with h1:
        if logo_path:
            st.image(str(logo_path), use_container_width=True)
    with h2:
        st.markdown("# Toastmasters Evaluation Assistant (T.E.A.)")
        st.caption(
            "Turn rubric ratings + rough notes into a structured, project-aligned evaluation draft. "
            "Export uses a form-style layout aligned to the official Toastmasters evaluation form."
        )


def render_step_indicator():
    page = st.session_state.get("page", "select")
    steps = [
        ("Step 1/4", "Select Project Details", "select"),
        ("Step 2/4", "Load Project", "loading"),
        ("Step 3/4", "Evaluation Form", "evaluation"),
        ("Step 4/4", "Draft & Export", "draft"),
    ]
    page_to_idx = {"select": 0, "loading": 1, "evaluation": 2, "draft_loading": 3, "draft": 3}
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
        speaker_name = st.text_input("Speaker Name", value=st.session_state.meeting.get("speaker", ""), placeholder="e.g., Oscar Zhu")
    with c2:
        evaluator_name = st.text_input("Evaluator Name", value=st.session_state.meeting.get("evaluator", ""), placeholder="e.g., Lee Ching Yuh")
    with c3:
        meeting_date = st.date_input("Date of Chapter Meeting", value=st.session_state.meeting.get("date"))

    speech_title = st.text_input("Speech Title", value=st.session_state.meeting.get("speech_title", ""), placeholder="e.g., Living with Dignity")

    st.session_state.meeting = {"speaker": speaker_name, "evaluator": evaluator_name, "date": meeting_date, "speech_title": speech_title}

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
        st.session_state.draft_md = ""
        st.session_state.pending_generation = None
        st.session_state.page = "select"
        st.rerun()

    if get_details:
        level_block = extract_level_block(md_path, level)
        if not level_block:
            st.error(f"❌ Level '{level}' not found in {md_path.name}.")
            st.stop()

        proj_block = extract_project_block(level_block, project)
        if not proj_block:
            st.error(f"❌ '{project}' not found under **{level}** in **{md_path.name}**.")
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
        st.session_state.page = "loading"
        st.rerun()

    st.caption(f"Using file: {md_path}")


# ==================== PAGE 2: LOADING ====================
if st.session_state.page == "loading":
    render_header()
    render_step_indicator()
    st.divider()

    st.subheader("Loading project details…")
    st.caption("Please wait while we prepare the evaluation form.")
    bar = st.progress(0)
    for i in range(101):
        bar.progress(i)
        time.sleep(0.02)

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

    top1, top2 = st.columns([1, 1])
    with top1:
        if st.button("⬅ Back"):
            st.session_state.page = "select"
            st.rerun()
    with top2:
        if st.button("🧹 Clear All"):
            st.session_state.details = None
            st.session_state.draft_md = ""
            st.session_state.pending_generation = None
            st.session_state.page = "select"
            st.rerun()

    d = st.session_state.details
    meeting = st.session_state.meeting
    meeting_date = meeting.get("date")
    meeting_date_str = str(meeting_date) if meeting_date else "N/A"

    st.subheader("Project Details")
    st.markdown('<div class="tea-narrow">', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Pathway**"); st.write(d["pathway"])
        st.markdown("---")
        st.markdown("**Level focus**"); st.write(d["level_focus"])
        st.markdown("---")
        st.markdown("**Purpose**"); st.write(d["purpose"])
        st.markdown("---")
        st.markdown("**Speech length**"); st.write(d["speech_len"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    st.subheader("Rubric Ratings (1–5)")
    st.caption("Rule: ratings 4–5 → Strengths, ratings 1–3 → Areas for improvement.")

    if is_ice_breaker(d["project"]):
        with st.expander("View Evaluation Criteria (Ice Breaker)"):
            render_full_ice_breaker_criteria()

    rubric_items = render_rubric_table(RUBRIC_DEF)

    total_score = compute_total_score(rubric_items)
    max_score = len(rubric_items) * 5
    label, style = overall_band(total_score)

    st.subheader("Speaker's Competency Total Accumulated Score")
    cA, cB = st.columns([1.2, 2.8], vertical_alignment="center")
    with cA:
        st.metric("Total Score", f"{total_score} / {max_score}")
    with cB:
        st.progress(total_score / max_score if max_score else 0)

    if style == "success":
        st.success(f"Overall Result: {label}")
    elif style == "info":
        st.info(f"Overall Result: {label}")
    elif style == "warning":
        st.warning(f"Overall Result: {label}")
    else:
        st.error(f"Overall Result: {label}")

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
    st.subheader("General Comments - By Project Speech Evaluator")
    st.caption("Tip: Fill at least one box OR add at least one rubric comment.")

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
- Target speech length: {d["speech_len"]}

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
                st.session_state.pending_generation = {
                    "notes_payload": notes_payload,
                    "pathway": d.get("pathway", ""),
                    "level": d.get("level", ""),
                    "project": d.get("project", ""),
                    "level_focus": d.get("level_focus", ""),
                    "purpose": d.get("purpose", ""),
                    "speech_len": d.get("speech_len", ""),
                    "criteria_text": selected_criteria_text,
                    "total_score": total_score,
                    "score_band": label,
                    "meeting": {
                        "speaker": meeting.get("speaker", ""),
                        "evaluator": meeting.get("evaluator", ""),
                        "meeting_date": meeting_date_str,
                        "speech_title": meeting.get("speech_title", ""),
                    },
                }
                st.session_state.page = "draft_loading"
                st.rerun()

    st.caption(f"Using file: {d.get('md_path', '')}")


# ==================== PAGE 4: DRAFT LOADING ====================
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

    p = st.progress(0)
    for i in range(30):
        p.progress(int((i + 1) / 30 * 100))
        time.sleep(0.1)

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
            speaker_name=(pending.get("meeting", {}) or {}).get("speaker", ""),
            evaluator_name=(pending.get("meeting", {}) or {}).get("evaluator", ""),
            meeting_date=(pending.get("meeting", {}) or {}).get("meeting_date", ""),
            speech_title=(pending.get("meeting", {}) or {}).get("speech_title", ""),
            total_score=pending.get("total_score"),
            score_band=pending.get("score_band", ""),
        )

    st.session_state.draft_md = output
    st.session_state.page = "draft"
    st.rerun()


# ==================== PAGE 5: DRAFT + EXPORT ====================
if st.session_state.page == "draft":
    render_header()
    render_step_indicator()

    pending = st.session_state.get("pending_generation") or {}
    meeting_export = (pending.get("meeting") or {}).copy()

    st.subheader("Evaluation draft (editable)")
    draft_default = st.session_state.get("draft_md") or ""
    edited = st.text_area("You can edit the draft below before exporting:", value=draft_default, height=520, key="draft_editor")

    st.divider()

    # Optional: show extracted purpose-alignment summary for screenshot/reporting
    if purpose_alignment_summary is not None:
        s = purpose_alignment_summary(edited)
        if s:
            st.caption(f"Purpose Alignment Summary: {s}")

    st.subheader("Export (meeting-ready layout)")
    st.caption("HTML export is styled to closely match the official Toastmasters evaluation form layout.")

    # Build filenames
    ts = time.strftime("%Y%m%d_%H%M%S")
    md_name = f"tea_evaluation_draft_{ts}.md"
    html_name = f"tea_evaluation_form_{ts}.html"
    pdf_name = f"tea_evaluation_draft_{ts}.pdf"

    selection = {
        "pathway": pending.get("pathway", ""),
        "level": pending.get("level", ""),
        "project": pending.get("project", ""),
        "speech_len": pending.get("speech_len", ""),
        "purpose": pending.get("purpose", ""),
        "level_focus": pending.get("level_focus", ""),
    }

    html_out = build_export_html_form(
        title="Evaluation Form (Toastmasters - Meeting Ready)",
        meeting=meeting_export,
        selection=selection,
        draft_md=edited,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Download Markdown", data=edited.encode("utf-8"), file_name=md_name, mime="text/markdown", use_container_width=True)
    with c2:
        st.download_button("⬇️ Download HTML (Print → PDF)", data=html_out.encode("utf-8"), file_name=html_name, mime="text/html", use_container_width=True)
    with c3:
        pdf_bytes = make_pdf_bytes_simple("Toastmasters Evaluation Draft", edited)
        st.download_button(
            "⬇️ Download PDF (simple)",
            data=pdf_bytes if pdf_bytes else b"",
            file_name=pdf_name,
            mime="application/pdf",
            disabled=not bool(pdf_bytes),
            use_container_width=True,
        )
        if not pdf_bytes:
            st.caption("Direct PDF needs ReportLab (reportlab>=4.0). HTML export is recommended for best formatting.")

    st.info("Best PDF quality: download the HTML → open in Chrome/Edge → Print → Save as PDF.")

    st.divider()
    back1, back2 = st.columns(2)
    with back1:
        if st.button("⬅ Back to Evaluation Form"):
            st.session_state.page = "evaluation"
            st.rerun()
    with back2:
        if st.button("🏠 Start Over"):
            st.session_state.page = "select"
            st.session_state.details = None
            st.session_state.draft_md = ""
            st.session_state.pending_generation = None
            st.rerun()

    st.stop()
