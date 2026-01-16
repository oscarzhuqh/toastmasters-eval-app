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

LEVELS = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]

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
        "Effective Body Language",
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
        (i for i in range(proj_start + 1, len(lines)) if lines[i].strip()._

