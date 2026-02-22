# Toastmasters Evaluation Assistant (T.E.A.)

## Overview
The Toastmasters Evaluation Assistant (T.E.A.) is a Streamlit-based web application that supports evaluators in producing structured, project-aligned speech evaluations. The system uses a constrained Generative AI workflow grounded in official Toastmasters Pathways documentation, with mandatory human-in-the-loop review.

## Key Files
- **app.py** — Application orchestration and Streamlit user interface. Manages user input, workflow control, AI invocation, human review, and export.
- **crewai_eval.py** — AI-assisted evaluation logic. Constructs bounded prompts using retrieved Pathways context and evaluator inputs, performs draft generation and alignment verification, and returns a structured evaluation draft.
- **/knowledge/** — Local Markdown-based knowledge base containing official Toastmasters Pathways documentation used for retrieval-augmented generation.

## Technology Stack
- Frontend: Streamlit
- AI Services: OpenAI-compatible LLM (gpt-4o-mini)
- Orchestration: CrewAI
- Retrieval: Local Markdown knowledge base (RAG)

## Notes
This repository focuses on application development and responsible AI integration. Final evaluation outputs always require human review and approval.
