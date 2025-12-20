import streamlit as st

st.title("Toastmasters Evaluation Assistant (Test)")

# Input fields
speaker_name = st.text_input("Speaker Name")
speech_title = st.text_input("Speech Title")
evaluator_name = st.text_input("Evaluator Name")

notes = st.text_area("Paste evaluator notes", height=200)

if st.button("Generate Evaluation"):
    if not notes.strip():
        st.warning("Please enter some notes.")
    else:
        st.success("Structured preview generated successfully.")

        # Display raw notes
        st.subheader("Evaluator Notes (Raw)")
        st.text(notes)

        # --- Simple rule-based processing ---
        positive_keywords = ["good", "strong", "clear", "confident", "effective", "well"]
        improve_keywords = ["improve", "need", "lack", "smile", "rushed", "weak", "more"]

        strengths = []
        improvements = []

        for line in notes.split("\n"):
            line_lower = line.lower()
            if any(word in line_lower for word in improve_keywords):
                improvements.append(line.strip())
            elif any(word in line_lower for word in positive_keywords):
                strengths.append(line.strip())

        # --- Structured Output ---
        st.subheader("Structured Evaluation Preview")

        st.markdown(f"""
### Opening
Thank you, **{speaker_name if speaker_name else "Speaker"}**, for your speech{f" titled *{speech_title}*" if speech_title else ""}. I appreciate the effort you put into preparing and delivering your message to the audience.
""")

        st.markdown("### Commendations")
        if strengths:
            for s in strengths:
                st.write(f"- {s.capitalize()}")
        else:
            st.write("- Good effort and confidence shown during the speech.")

        st.markdown("### Areas for Improvement")
        if improvements:
            for i in improvements:
                st.write(f"- {i.capitalize()}")
        else:
            st.write("- Continue refining delivery and audience engagement.")

        st.markdown(f"""
### Encouraging Close
Overall, this was a solid speech with a strong foundation. With continued practice and small improvements, your future speeches will become even more impactful.

— *Evaluation by {evaluator_name if evaluator_name else "Evaluator"}*
""")


