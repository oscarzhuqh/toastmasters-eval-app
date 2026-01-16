import streamlit as st
from pathlib import Path
import re

# ✅ Change this to your actual .md file
MD_PATH = Path("knowledge/pathways/presentation_mastery.md")

def extract_purpose(md_path: Path, level: str, project: str) -> str:
    if not md_path.exists():
        return f"Markdown file not found: {md_path}"

    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find Level block
    level_header = f"## {level}"
    level_start = next((i for i, line in enumerate(lines) if line.strip().lower() == level_header.lower()), None)
    if level_start is None:
        return f"Level '{level}' not found."

    level_end = next((i for i in range(level_start + 1, len(lines)) if lines[i].strip().startswith("## ")), len(lines))
    level_block = lines[level_start:level_end]

    # Find Project block within Level
    project_header = f"### Project: {project}"
    proj_start = next((i for i, line in enumerate(level_block) if line.strip().lower() == project_header.lower()), None)
    if proj_start is None:
        return f"Project '{project}' not found under {level}."

    proj_end = next((i for i in range(proj_start + 1, len(level_block)) if level_block[i].strip().startswith("### Project:")), len(level_block))
    proj_block = "\n".join(level_block[proj_start:proj_end])

    # Extract purpose (supports your current style)
    # e.g. "- **Purpose ...:** some text"
    m = re.search(r"\*\*Purpose.*?\*\*:\s*(.+)", proj_block, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return "Purpose not found. Make sure the line looks like: - **Purpose...**: <text>"

st.title("Toastmasters Purpose Retriever (Test)")

st.write("Reads purpose from local Markdown knowledge base.")

level = st.selectbox("Select Level", ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"])
project = st.text_input("Project name (must match Markdown heading)", "Ice Breaker")

if st.button("Get Purpose"):
    purpose = extract_purpose(MD_PATH, level, project)
    st.subheader("Purpose")
    st.write(purpose)

st.caption(f"Using file: {MD_PATH}")
