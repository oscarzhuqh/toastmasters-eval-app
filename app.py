import streamlit as st
from pathlib import Path
import re

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

# Example project lists (you can edit anytime)
LEVEL_PROJECTS = {
    "Level 1": [
        "Ice Breaker",
        "Evaluation and Feedback (1st Speech)",
        "Evaluation and Feedback (2nd Speech)",
        "Introduction to Vocal Variety and Body Language",
        "Writing a Speech with Purpose",
    ],
    "Level 2": [
        "Connect with Your Audience",
        "Introduction to Toastmasters Mentoring",
        "Understanding Your Leadership Style",
        "Understanding Your Communication Style",
        "Active Listening",
         "Managing Time",
    ],
    "Level 3": [
        "Persuasive Speaking",
        "Connect with Storytelling",
        "Deliver Social Speeches",
        "Using Presentation Software",
    ],
    "Level 4": [
        "Manage Online Meetings",
        "Public Relations Strategies",
    ],
    "Level 5": [
        "High Performance Leadership",
        "Prepare to Speak Professionally",
    ],
}

# -------------------- PARSERS --------------------
def extract_level_block(md_path: Path, level: str) -> str | None:
    """Return the full markdown block for a given level heading like '## Level 2'."""
    if not md_path.exists():
        return None

    lines = md_path.read_text(encoding="utf-8").splitlines()
    level_header = f"## {level}"

    level_start = next((i for i, line in enumerate(lines) if line.strip().lower() == level_header.lower()), None)
    if level_start is None:
        return None

    level_end = next((i for i in range(level_start + 1, len(lines)) if lines[i].strip().startswith("## ")), len(lines))
    return "\n".join(lines[level_start:level_end])

def extract_level_focus(level_block: str) -> str | None:
    # Supports: **Level focus (your words):** text (colon inside/outside bold, spaces ok)
    m = re.search(r"\*\*Level focus.*?\*\*\s*:?\s*(.+)", level_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None

def extract_project_block(level_block: str, project: str) -> str | None:
    """Return the project section under a given level block."""
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
    """
    Supports lines like:
      - **Purpose**: text
      - **Purpose:** text
      - **Speech length (optional)**: text
      - **Speech length**: text
    (colon can be inside/outside bold; spaces around colon ok)
    """
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*?\s*:?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


# -------------------- UI --------------------
st.set_page_config(page_title="Toastmasters Project Details", page_icon="🗂️", layout="centered")
st.title("Toastmasters Project Details")

pathway = st.selectbox("Select Pathway", list(PATHWAY_FILES.keys()))
level = st.selectbox("Select Level", LEVELS)

# ✅ Project dropdown changes with Level
project_options = LEVEL_PROJECTS.get(level, [])
if not project_options:
    st.warning(f"No project list configured for {level}. Add it in LEVEL_PROJECTS.")
  available = re.findall(r"^###\s*Project:\s*(.+)\s*$", level_block, flags=re.IGNORECASE | re.MULTILINE)
if available:
    st.caption("Projects found in this pathway + level:")
    st.write(available)

    st.stop()

project = st.selectbox("Select Project", project_options, key=f"project_{level}")

md_path = KB_DIR / PATHWAY_FILES[pathway]

if st.button("Get Details"):
    if not md_path.exists():
        st.error(f"Markdown file not found for '{pathway}'. Expected: {md_path}")
        st.stop()

    level_block = extract_level_block(md_path, level)
    if not level_block:
        st.error(f"Level '{level}' not found in {md_path.name}.")
        st.info("Fix: Add a heading like `## Level 2` into the markdown file.")
        st.stop()

    proj_block = extract_project_block(level_block, project)
    if not proj_block:
        st.error(f"Project '{project}' not found under {level} in {md_path.name}.")
        st.info(f"Fix: Ensure your markdown has exactly: `### Project: {project}`")
        st.stop()

    level_focus = extract_level_focus(level_block) or "Not found"
    purpose = extract_field(proj_block, "Purpose") or "Not found"

    speech_len = (
        extract_field(proj_block, "Speech length (optional)")
        or extract_field(proj_block, "Speech length")
        or "Not found"
    )

    st.subheader("Project Details")
    with st.container(border=True):
        st.markdown("### Pathway")
        st.write(pathway)

        st.markdown("---")
        st.markdown("### Level focus")
        st.write(level_focus)

        st.markdown("---")
        st.markdown("### Purpose")
        st.write(purpose)

        st.markdown("---")
        st.markdown("### Speech length")
        st.write(speech_len)

st.caption(f"Using file: {md_path}")


