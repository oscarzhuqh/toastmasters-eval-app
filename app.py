from crewai_eval import run_crewai_eval

st.markdown("## Evaluator Notes")
notes = st.text_area("Paste your rough notes (bullet points ok):", height=160)

if st.button("Generate Evaluation Draft (CrewAI)"):
    if not notes.strip():
        st.warning("Please paste some evaluator notes first.")
    else:
        draft = run_crewai_eval(
            notes=notes,
            pathway=pathway,
            level=level,
            project=project,
            level_focus=level_focus,
            purpose=purpose,
            speech_len=speech_len,
        )
        st.markdown("## CrewAI Output")
        st.write(draft)

