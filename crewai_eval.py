import os

from crewai import Agent, Task, Crew

def run_crewai_eval(
    *,
    notes: str,
    pathway: str,
    level: str,
    project: str,
    level_focus: str,
    purpose: str,
    speech_len: str,
) -> str:
    """
    Retrieval = your markdown extraction (level_focus/purpose/speech_len)
    Generation = CrewAI turns your notes into a structured evaluation draft
    """

    # Expect API key to be set via Streamlit Secrets or env var
    if not os.getenv("OPENAI_API_KEY"):
        return (
            "OPENAI_API_KEY not set.\n\n"
            "Fix: In Streamlit Cloud -> App -> Settings -> Secrets, add:\n"
            'OPENAI_API_KEY="your_key_here"'
        )

    context = f"""
Pathway: {pathway}
Level: {level}
Project: {project}

Level focus:
{level_focus}

Project purpose:
{purpose}

Speech length:
{speech_len}

Evaluator raw notes (do not invent facts):
{notes}
""".strip()

    drafting_agent = Agent(
        role="Toastmasters Evaluation Drafting Assistant",
        goal="Write a supportive, structured Toastmasters evaluation aligned to the selected project purpose.",
        backstory="You are experienced in Toastmasters evaluations and write concise, actionable feedback.",
        allow_delegation=False,
    )

    qa_agent = Agent(
        role="Evaluation Quality Checker",
        goal="Ensure the evaluation is aligned to purpose and does not add facts not in the notes.",
        backstory="You check for clarity, fairness, and actionable recommendations.",
        allow_delegation=False,
    )

    draft_task = Task(
        description=(
            "Using ONLY the provided context + evaluator notes, write a structured evaluation in markdown:\n"
            "1) Commendations (2–3 bullets, specific)\n"
            "2) Recommendations (2–3 bullets, actionable + kind)\n"
            "3) Next time plan (1 sentence)\n"
            "4) Encouraging close (1 sentence)\n\n"
            "Rules:\n"
            "- Do NOT invent content that isn't in the notes.\n"
            "- Keep it concise and practical.\n\n"
            f"CONTEXT:\n{context}"
        ),
        expected_output="A clean evaluation draft in markdown.",
        agent=drafting_agent,
    )

    qa_task = Task(
        description=(
            "Review the draft and produce:\n"
            "A) Alignment check (3 bullets): purpose covered? notes respected? actionable?\n"
            "B) Final draft (revise only if needed; otherwise repeat draft unchanged)\n\n"
            "Rules:\n"
            "- Do NOT add new facts beyond the notes.\n"
        ),
        expected_output="Alignment check + final evaluation draft in markdown.",
        agent=qa_agent,
    )

    crew = Crew(
        agents=[drafting_agent, qa_agent],
        tasks=[draft_task, qa_task],
        verbose=False,
    )

    result = crew.kickoff()
    return getattr(result, "raw", str(result))
