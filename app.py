import streamlit as st
from pathlib import Path
import re

from crewai_eval import run_crewai_eval  # <-- NEW

# -------------------- CONFIG --------------------
KB_DIR = Path(__file__).parent / "knowledge" / "pathways"

PATHWAY_FILES = {
    "Dynamic Leadership": "dynamic_leadership.md",
    "Engaging Humor": "engaging_humor.md",
    "Motivational Strategies": "motivational_strategies.md",
    "Persuasive Influence": "persuasive_influence.md",
    "Presentation Mastery": "presentation_mastery.md",
    "Visionary Communication": "visionary_communication.md",
}

LEVELS = ["Level 1", "Level 2"]

# -------------------- PARSERS --------------------
def extract_level_block(md_path: Path, level: str) -> str | None:
    if not md_path.exists():
        return None

    lines = md_path.read_text(encoding="utf-8").splitlines()
    level_header = f"## {level}"

    level_start = next((i for i, line in enumerate(lines) if line.strip().lower() == level_header.lower()), None)
    if level_start is None:
        return None

    level_end = next(
        (i for i in range(level_start + 1, len(lines)) if lines[i].strip().startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[level_start:level_end])

def extract_level_focus(level_block: str) -> str | None:
    m = re.search(r"\*\*Level focus.*?\*\*\s*:?\s*(.+)", level_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None

def get_projects_from_markdown(md_path: Path, level: str) -> list[str]:
    level_block = extract_level_block(md_path, level)
    if not level_block:
        return []
    return re.findall(r"^###\s*Project:\s*(.+)\s*$", level_block, flags=re.IGNORECASE | re.MULTILINE)

def extract_project_block(level_block: str, project: str) -> str | None:
    lines = level_block.splitlines()
    project_header = f"### Project: {project}"

    proj_start = next((i for i, line in enumerate(lines) if line.strip().lower() == project_header.lower()), None)
    if proj_start is None:
        return None

    proj_end = next(
        (i for i in range(proj_start + 1, len(lines)) if lines[i].strip().startswith("### Project:")),
        len(lines),
    )
    return "\n".join(lines[proj_start:proj_end])

def extract_field(proj_block: str, field_name: str) -> str | None:
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*?\s*:?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None

# -------------------- UI --------------------
st.set_page_config(page_title="Toastmasters Project Details", page_icon="🗂️", layout="centered")
st.title("Toastmasters Project Details")

# session state init
if "details" not in st.session_state:
    st.session_state.details = None
if "crewai_output" not in st.session_state:
    st.session_state.crewai_output = None

pathway = st.selectbox("Select Pathway", list(PATHWAY_FILES.keys()))
level = st.selectbox("Select Level", LEVELS)

md_path = KB_DIR / PATHWAY_FILES[pathway]

if not md_path.exists():
    st.error(f"Markdown file not found for '{pathway}'. Expected: {md_path}")
    st.stop()

project_options = get_projects_from_markdown(md_path, level)
if not project_options:
    st.warning(
        f"No projects found for {level} in '{md_path.name}'.\n\n"
        "Add headings like:\n"
        "### Project: Ice Breaker"
    )
    st.stop()

project = st.selectbox("Select Project", project_options, key=f"project_{pathway}_{level}")

col1, col2 = st.columns([1, 1])
with col1:
    get_details = st.button("Get Details")
with col2:
    clear = st.button("Clear")

if clear:
    st.session_state.details = None
    st.session_state.crewai_output = None
    st.rerun()

# ----- Get Details -----
if get_details:
    level_block = extract_level_block(md_path, level)
    if not level_block:
        st.error(f"❌ Level '{level}' not found in {md_path.name}.")
        st.info("Fix: Add a heading like `## Level 2` into the markdown file.")
        st.stop()

    proj_block = extract_project_block(level_block, project)
    if not proj_block:
        st.error(
            f"❌ '{project}' was not found under {level} for the '{pathway}' pathway.\n\n"
            "✅ Please ensure you selected the correct pathway OR add this project into the pathway markdown file."
        )
        available = re.findall(r"^###\s*Project:\s*(.+)\s*$", level_block, flags=re.IGNORECASE | re.MULTILINE)
        if available:
            st.caption("Projects found in this pathway + level:")
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
    }
    st.session_state.crewai_output = None  # reset old output

# ----- Display Details (if available) -----
if st.session_state.details:
    d = st.session_state.details

    st.subheader("Project Details")
    with st.container(border=True):
        st.markdown("### Pathway")
        st.write(d["pathway"])

        st.markdown("---")
        st.markdown("### Level focus")
        st.write(d["level_focus"])

        st.markdown("---")
        st.markdown("### Purpose")
        st.write(d["purpose"])

        st.markdown("---")
        st.markdown("### Speech length")
        st.write(d["speech_len"])

    st.markdown("## Evaluator Notes")
    notes = st.text_area("Paste your rough notes (bullet points ok):", height=160)

    if st.button("Generate Evaluation Draft (CrewAI)"):
        if not notes.strip():
            st.warning("Please paste some evaluator notes first.")
        else:
            output = run_crewai_eval(
                notes=notes,
                pathway=d["pathway"],
                level=d["level"],
                project=d["project"],
                level_focus=d["level_focus"],
                purpose=d["purpose"],
                speech_len=d["speech_len"],
            )
            st.session_state.crewai_output = output

    if st.session_state.crewai_output:
        st.markdown("## CrewAI Output")
        st.write(st.session_state.crewai_output)

st.caption(f"Using file: {md_path}")

