import streamlit as st
from pathlib import Path
import re

# Folder where your pathway markdown files live
KB_DIR = Path(__file__).parent / "knowledge" / "pathways"

# 6 pathways dropdown + expected filenames
PATHWAY_FILES = {
    "Dynamic Leadership": "dynamic_leadership.md",
    "Engaging Humor": "engaging_humor.md",
    "Motivational Strategies": "motivational_strategies.md",
    "Persuasive Influence": "persuasive_influence.md",
    "Presentation Mastery": "presentation_mastery.md",
    "Visionary Communication": "visionary_communication.md",
}

LEVELS = ["Level 1"]

LEVEL_1_PROJECTS = [
    "Ice Breaker",
    "Evaluation and Feedback (1st Speech)",
    "Evaluation and Feedback (2nd Speech)",
    "Introduction to Vocal Variety and Body Language",
    "Writing a Speech with Purpose",
]

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

def extract_level_focus(level_block: str) -> str | None:
    # Supports: **Level focus (your words):** text (spaces ok, colon inside/outside bold ok)
    m = re.search(r"\*\*Level focus.*?\*\*\s*:?\s*(.+)", level_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None

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
    """
    Supports:
      - **Purpose**: text
      - **Purpose:** text
      - **Speech length (optional)**: text
      - **Speech length**: text
    """
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*?\s*:?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


# ---------------- UI ----------------
st.set_page_config(page_title="Toastmasters KB", page_icon="🗂️", layout="centered")
st.title("Toastmasters Project Details")

pathway = st.selectbox("Select Pathway", list(PATHWAY_FILES.keys()))
level = st.selectbox("Select Level", LEVELS)
project = st.selectbox("Select Project", LEVEL_1_PROJECTS)

md_path = KB_DIR / PATHWAY_FILES[pathway]

if st.button("Get Details"):
    if not md_path.exists():
        st.error(
            f"Markdown file not found for '{pathway}'.\n\n"
            f"Expected: {md_path}\n\n"
            "Create/upload the file into knowledge/pathways/."
        )
        st.stop()

    level_block = extract_level_block(md_path, level)
    if not level_block:
        st.error(f"Level '{level}' not found in {md_path.name}.")
        st.stop()

    proj_block = extract_project_block(level_block, project)
    if not proj_block:
        st.error(
            f"Project '{project}' not found under {level} in {md_path.name}.\n\n"
            f"Make sure your markdown has exactly:\n"
            f"### Project: {project}"
        )
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

