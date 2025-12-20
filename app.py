import streamlit as st

st.title("Toastmasters Evaluation Assistant (Test)")

# Input fields
speaker_name = st.text_input("Speaker Name")
speech_title = st.text_input("Speech Title")
evaluator_name = st.text_input("Evaluator Name")

notes = st.text_area("Paste evaluator notes", height=200)

if st.button("Generate"):
    if not notes.strip():
        st.warning("Please enter some notes.")
    else:
        st.success("Structured preview generated successfully.")

        st.subheader("Evaluator Notes (Raw)")
        st.text(notes)

        st.subheader("Structured Evaluation Preview")

        st.markdown(f"""
### Opening
Thank you, **{speaker_name if speaker_name else "Speaker"}**, for your speech{f" titled *{speech_title}*" if speech_title else ""}. I appreciate the effort you put into preparing and delivering your message to the audience.

### Commendations
One of your strengths was your eye contact. You maintained good eye contact throughout the speech, which helped you appear confident and connected with the audience. This made it easier for listeners to stay engaged.

Your speech was also well structured. The flow of your ideas was generally clear, allowing the audience to follow your main points without confusion.

### Areas for Improvement
One area you may want to work on is audience engagement. While your eye contact was good, you could further engage the audience by varying your vocal tone, using gestures, or emphasising key points more clearly.

Another suggestion is to improve transitions between ideas. Smoother transitions will help your speech feel more cohesive and easier to follow.

### Encouraging Close
Overall, this was a solid speech with a strong foundation. With more focus on engaging the audience and refining your transitions, your future speeches will become even more impactful.

— *Evaluation by {evaluator_name if evaluator_name else "Evaluator"}*
""")


