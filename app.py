import streamlit as st
import requests

st.title("Toastmasters Evaluation Assistant")

notes = st.text_area("Paste evaluator notes")
length = st.selectbox("Evaluation length", ["1 minute", "2 minutes", "3 minutes"])

FLOWISE_URL = "http://localhost:3000/api/v1/prediction/YOUR_CHATFLOW_ID"

if st.button("Generate Evaluation"):
    if not notes.strip():
        st.warning("Please enter some notes.")
    else:
        payload = {
            "question": f"""
Evaluator notes:
{notes}

Evaluation length: {length}

Generate a structured Toastmasters evaluation with:
- Opening
- Commendations
- Recommendations
- Encouraging close

Use only the notes provided.
"""
        }

        response = requests.post(FLOWISE_URL, json=payload)

        if response.status_code == 200:
            result = response.json()
            st.subheader("Generated Evaluation")
            st.write(result["text"])
        else:
            st.error("Flowise request failed.")
