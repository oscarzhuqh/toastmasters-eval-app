import streamlit as st

st.title("Toastmasters Evaluation Assistant (Test)")

notes = st.text_area("Paste evaluator notes", height=200)

if st.button("Generate"):
    if not notes.strip():
        st.warning("Please enter some notes.")
    else:
        st.success("Notes received successfully.")

        st.subheader("Evaluator Notes (Raw)")
        st.text(notes)

        st.subheader("Structured Preview (Manual)")
        st.markdown("""
**Strengths:**
- Good energy
- Nice structure
- Eye contact mostly good

**Areas for Improvement:**
- Organise ideas more clearly
- Practise smoother transitions
- End with a clear conclusion
""")

