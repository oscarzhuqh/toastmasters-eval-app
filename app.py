import streamlit as st

st.title("Toastmasters Evaluation Assistant (Test)")

notes = st.text_area("Paste evaluator notes")

if st.button("Generate"):
    if not notes.strip():
        st.warning("Please enter some notes.")
    else:
        st.success("App is working!")
        st.write("Notes received:")
        st.write(notes)
