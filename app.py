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
    """Auto-build dropdown options from headings: ### Project: <name>"""
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

pathway = st.selectbox("Select Pathway", list(PATHWAY_FILES.keys()))
level = st.selectbox("Select Level", LEVELS)

md_path = KB_DIR / PATHWAY_FILES[pathway]

# ✅ Project dropdown is driven by the selected pathway + level markdown
project_options = get_projects_from_markdown(md_path, level)

if not md_path.exists():
    st.error(f"Markdown file not found for '{pathway}'. Expected: {md_path}")
    st.stop()

if not project_options:
    st.warning(
        f"No projects found for {level} in '{md_path.name}'.\n\n"
        "Add headings like:\n"
        "### Project: Ice Breaker"
    )
    st.stop()

project = st.selectbox("Select Project", project_options, key=f"project_{pathway}_{level}")

if st.button("Get Details"):
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

