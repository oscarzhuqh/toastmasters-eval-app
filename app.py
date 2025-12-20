import streamlit as st

st.image("toastmasters_logo.png", width=200)
st.title("Toastmasters Evaluation Assistant (Test)")

# -----------------------
# Input fields
# -----------------------
speaker_name = st.text_input("Speaker Name")
speech_title = st.text_input("Speech Title")
evaluator_name = st.text_input("Evaluator Name")

pathway = st.selectbox(
    "Toastmasters Pathways",
    [
        "---Please Select from this drop-down list--",
        "Dynamic Leadership",
        "Engaging Humor",
        "Motivational Strategies",
        "Persuasive Influence",
        "Presentation Mastery",
        "Visionary Communication",
        "Effective Coaching",
        "Innovative Planning",
        "Leadership Development",
        "Strategic Relationships",
        "Team Collaboration"
    ]
)

pathway_level = st.selectbox(
    "TPathway Level",
    [
        "---Please Select from this drop-down list--",
        "1",
        "2",
        "3",
        "4",
        "5",
        "DTM",
    ]
)
evaluation_length = st.selectbox(
    "Evaluation Length",
    ["1 minute", "2 minutes", "3 minutes"]
)

notes = st.text_area("Paste evaluator notes", height=200)

# -----------------------
# Generate Evaluation
# -----------------------
if st.button("Generate Evaluation"):
    if not notes.strip():
        st.warning("Please enter some notes.")
    else:
        st.success("Structured preview generated successfully.")

        # Display raw notes
        st.subheader("Evaluator Notes (Raw)")
        st.text(notes)

        # -----------------------
        # Simple rule-based processing
        # -----------------------
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

        # -----------------------
        # Length-based text control
        # -----------------------
        if evaluation_length == "1 minute":
            opening = "Thank you for your speech today. I appreciate the effort you put into sharing your message."
            commendation_prefix = "One key strength was"
            improvement_prefix = "One area to improve is"
            closing = "Overall, this was a good effort, and I encourage you to keep practising."

        elif evaluation_length == "2 minutes":
            opening = "Thank you for your speech today. I appreciate the effort you put into preparing and delivering your message to the audience."
            commendation_prefix = "One of your strengths was"
            improvement_prefix = "One area you may want to work on is"
            closing = "Overall, this was a solid speech with a strong foundation. With continued practice, your speeches will become even more impactful."

        else:  # 3 minutes
            opening = "Thank you for your speech today. I really enjoyed listening to your presentation and appreciate the effort you put into preparing and delivering your message to the audience."
            commendation_prefix = "One of your key strengths was"
            improvement_prefix = "One important area you could further improve on is"
            closing = "Overall, this was a strong and confident speech with good potential. With more focus on refining your delivery and engaging the audience, your future speeches will continue to improve."

        # -----------------------
        # Structured Output
        # -----------------------
        st.subheader("Structured Evaluation Preview")

        st.markdown(f"""
### Opening
Thank you, **{speaker_name if speaker_name else "Speaker"}**, for your speech{f" titled *{speech_title}*" if speech_title else ""}.  
This evaluation is aligned with the **{pathway}** pathway.  
{opening}
""")

        st.markdown("### Commendations")
        if strengths:
            for s in strengths[:2]:
                st.write(f"- {commendation_prefix} {s}.")
        else:
            st.write("- You demonstrated good effort and confidence during your speech.")

        st.markdown("### Areas for Improvement")
        if improvements:
            for i in improvements[:2]:
                st.write(f"- {improvement_prefix} {i}.")
        else:
            st.write("- Continue refining your delivery and audience engagement.")

        st.markdown(f"""
### Encouraging Close
{closing}

— *Evaluation by {evaluator_name if evaluator_name else "Evaluator"}*
""")

