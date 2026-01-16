import streamlit as st
from pathlib import Path
import re

# ✅ Robust path (works on Streamlit Cloud too)
MD_PATH = Path(__file__).parent / "knowledge" / "pathways" / "presentation_mastery.md"

def extract_field(proj_block: str, field_name: str) -> str | None:
    """
    Supports:
      - **Purpose**: text
      - **Purpose:** text
      - **Speech length (optional)**: text
      - **Speech length (optional):** text
    """
    # Match: - **Field ...**: value  (allow spaces around colon and colon inside/outside bold)
    pattern = rf"-\s*\*\*{re.escape(field_name)}.*?\*\*?\s*:?\s*(.+)"
    m = re.search(pattern, proj_block, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

def extract_project_block(md_path: Path, level: str, project: str) -> str | None:
    if not md_path.exists():
        return None

    lines = md_path.read_text(encoding="utf-8").splitlines()

    # Find Level section
    level_header = f"## {level}"
    level_start = next((i for i, line in enumerate(lines) if line.strip().lower() == level_header.lower()), None)
    if level_start is None:
        return None

    level_end = next((i for i in range(level_start + 1, len(lines)) if lines[i].strip().startswith("## ")), len(lines))
    level_block = lines[level_start:level_end]

    # Find Project section inside Level
    project_header = f"### Project: {project}"
    proj_start = next((i for i, line in enumerate(level_block) if line.strip().lower() == project_header.lower()), None)
    if proj_start is None:
        return None

    proj_end = next(
        (i for i in range(proj_start + 1, len(level_block)) if level_block[i].strip().startswith("### Project:")),
        len(level_block),
    )

    return "\n".join(level_block[proj_start:proj_end])

st.set_page_config(page_title="Toastmasters KB Test", page_icon="🗂️", layout="centered")

st.title("Toastmasters Purpose Retriever (Test)")
st.write("Reads project details from a local Markdown knowledge base.")

level = st.selectbox("Select Level", ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"])
project = st.text_input("Project name (must match Markdown heading)", "Ice Breaker")

if st.button("Get Purpose"):
    proj_block = extract_project_block(MD_PATH, level, project)

    if proj_block is None:
        st.error(f"Not found. Check file path and headings.\n\nUsing file: {MD_PATH}")
    else:
        purpose = extract_field(proj_block, "Purpose") or "Not found"
        speech_len = extract_field(proj_block, "Speech length (optional)") \
                     or extract_field(proj_block, "Speech length") \
                     or "Not found"

        # ✅ Nice drawn box
        st.subheader("Project Details")
        with st.container(border=True):
            st.markdown("### Purpose")
            st.write(purpose)

            st.markdown("---")
            st.markdown("### Speech length")
            st.write(speech_len)

st.caption(f"Using file: {MD_PATH}")

