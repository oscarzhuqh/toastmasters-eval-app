import streamlit as st
from pathlib import Path
import re

# ✅ Update this path if your file name/location differs
MD_PATH = Path(__file__).parent / "knowledge" / "pathways" / "presentation_mastery.md"

# ✅ Hard-coded dropdown options (Level 1 only for now)
LEVELS = ["Level 1"]  # you can add "Level 2"..."Level 5" later

LEVEL_1_PROJECTS = [
    "Ice Breaker",
    "Evaluation and Feedback (First Speech)",
    "Evaluation and Feedback (Second Speech)",
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
    # Supports: **Level focus (your words):** text  (colon inside/outside bold, spaces ok)
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
      (colon can be inside/outside bold; spaces around colon are ok)
    """
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*?\s*:?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None

# ---------------- UI ----------------
st.set_page_config(page_title="Toastmasters KB (Level 1)", page_icon="🗂️", layout="centered")

st.title("Toastmasters Project Details (Level 1)")
st.write("Select a Level 1 project and retrieve details from your local Markdown knowledge base.")

level = st.selectbox("Select Level", LEVELS)

# Only Level 1 projects for now
project = st.selectbox("Select Project", LEVEL_1_PROJECTS)

if st.button("Get Details"):
    if not MD_PATH.exists():
        st.error(f"Markdown file not found: {MD_PATH}")
        st.stop()

    level_block = extract_level_block(MD_PATH, level)
    if not level_block:
        st.error(f"Level '{level}' not found in the Markdown file.\n\nUsing file: {MD_PATH}")
        st.stop()

    proj_block = extract_project_block(level_block, project)
    if not proj_block:
        st.error(
            f"Project '{project}' not found under {level}.\n\n"
            f"Make sure your markdown has a heading exactly like:\n"
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
        st.markdown("### Level focus")
        st.write(level_focus)

        st.markdown("---")
        st.markdown("### Purpose")
        st.write(purpose)

        st.markdown("---")
        st.markdown("### Speech length")
        st.write(speech_len)

st.caption(f"Using file: {MD_PATH}")
