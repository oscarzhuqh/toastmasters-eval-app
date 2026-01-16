import streamlit as st
from pathlib import Path
import re

# ✅ Robust path (works on Streamlit Cloud too)
MD_PATH = Path(__file__).parent / "knowledge" / "pathways" / "presentation_mastery.md"

def extract_level_block(md_path: Path, level: str) -> str | None:
    """Return the full markdown block for a given level (e.g., 'Level 1')."""
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
    """
    Supports both:
      **Level focus (your words):** text
      **Level focus (your words)**: text
    """
    # allow ':' inside or outside bold, and spaces around ':'
    m = re.search(r"\*\*Level focus.*?\*\*\s*:?\s*(.+)", level_block, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

def extract_project_block(md_path: Path, level: str, project: str) -> str | None:
    level_block = extract_level_block(md_path, level)
    if not level_block:
        return None

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
      - **Speech length (optional):** text
    """
    # allow colon inside/outside bold + spaces around colon
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*?\s*:?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


st.set_page_config(page_title="Toastmasters KB Test", page_icon="🗂️", layout="centered")

st.title("Toastmasters Purpose Retriever (Test)")
st.write("Reads project details from a local Markdown knowledge base.")

level = st.selectbox("Select Level", ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"])
project = st.text_input("Project name (must match Markdown heading)", "Ice Breaker")

if st.button("Get Speech Details"):
    if not MD_PATH.exists():
        st.error(f"Markdown file not found: {MD_PATH}")
    else:
        level_block = extract_level_block(MD_PATH, level)
        proj_block = extract_project_block(MD_PATH, level, project)

        if not level_block:
            st.error(f"Level '{level}' not found.\n\nUsing file: {MD_PATH}")
        elif not proj_block:
            st.error(f"Project '{project}' not found under {level}.\n\nUsing file: {MD_PATH}")
        else:
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


