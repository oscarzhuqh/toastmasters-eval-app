import streamlit as st
from datetime import date

# -----------------------
# Page config
# -----------------------
st.set_page_config(
    page_title="Toastmasters Evaluation Assistant (TEA)",
    page_icon="🗣️",
    layout="wide"
)

# -----------------------
# Header
# -----------------------
try:
    st.image("toastmasters_logo.png", width=180)
except Exception:
    pass

st.title("Toastmasters Evaluation Assistant (TEA) — Rubric-Based")
st.caption("Rubric scoring + comments to help you generate a structured evaluation. (Student prototype)")

# -----------------------
# Inputs (basic info)
# -----------------------
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        speaker_name = st.text_input("Speaker Name")
        speech_title = st.text_input("Speech Title")
    with c2:
        evaluator_name = st.text_input("Evaluator Name")
        meeting_date = st.date_input("Meeting Date", value=date.today())
    with c3:
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
            ],
            index=0
        )
        pathway_level = st.selectbox(
            "Pathway Level",
            ["---Please Select from this drop-down list--", "1", "2", "3", "4", "5", "DTM"],
            index=0
        )

st.divider()

# -----------------------
# Rubric definition
# -----------------------
RATING_LABELS = {
    5: "5 — Exemplary",
    4: "4 — Excels",
    3: "3 — Accomplished",
    2: "2 — Emerging",
    1: "1 — Developing",
}

RUBRICS = [
    {"key": "clarity", "title": "Clarity", "desc": "Spoken language is clear and is easily understood."},
    {"key": "vocal_variety", "title": "Vocal Variety", "desc": "Uses tone, speed, and volume as tools."},
    {"key": "eye_contact", "title": "Eye Contact", "desc": "Effectively uses eye contact to engage audience."},
    {"key": "gestures", "title": "Gestures", "desc": "Uses physical gestures effectively."},
    {"key": "audience_awareness", "title": "Audience Awareness", "desc": "Demonstrates awareness of audience engagement and needs."},
    {"key": "comfort_level", "title": "Comfort Level", "desc": "Appears comfortable with the audience."},
    {"key": "interest", "title": "Interest", "desc": "Engages audience with interesting, well-constructed content."},
    {"key": "well_supported", "title": "Well Supported", "desc": "Speech content is well-supported and sources are available if requested."},
]

# -----------------------
# Evaluation controls
# -----------------------
cA, cB, cC = st.columns([1.2, 1.2, 2])
with cA:
    evaluation_length = st.selectbox("Evaluation Length", ["1 minute", "2 minutes", "3 minutes"], index=1)
with cB:
    tone = st.selectbox("Evaluation Tone", ["Supportive Coach", "Professional Mentor", "Neutral/Contest-Style"], index=0)
with cC:
    focus = st.multiselect(
        "Rubric criteria to include (you can focus on fewer to reduce workload)",
        [r["title"] for r in RUBRICS],
        default=[r["title"] for r in RUBRICS],
    )

st.divider()

# -----------------------
# Rubric scoring UI
# -----------------------
st.subheader("Rubric Scoring (1–5) + Comments")
st.caption("Tip: If you’re short on time, score only 3–5 criteria and add brief comments.")

rubric_data = {}
for r in RUBRICS:
    if r["title"] not in focus:
        continue

    left, right = st.columns([2, 1.2])

    with left:
        st.markdown(f"**{r['title']}**: {r['desc']}")
        rating = st.radio(
            label=f"{r['title']} rating",
            options=[5, 4, 3, 2, 1],
            format_func=lambda x: RATING_LABELS[x],
            horizontal=True,
            index=2,
            key=f"rating_{r['key']}",
            label_visibility="collapsed",
        )

    with right:
        comment = st.text_area(
            "Comment (optional)",
            placeholder="What did you observe? One concrete example is enough.",
            height=80,
            key=f"comment_{r['key']}",
        )

    rubric_data[r["key"]] = {"title": r["title"], "rating": rating, "comment": comment.strip()}

st.divider()

# -----------------------
# Optional raw notes (keep for backward compatibility)
# -----------------------
with st.expander("Optional: Paste raw evaluator notes (if you have them)", expanded=False):
    notes = st.text_area("Paste evaluator notes", height=160, placeholder="You can leave this empty if you used the rubric above.")
    st.caption("This is optional. The rubric scores + comments are the primary inputs.")

# -----------------------
# Helper: build text by length + tone
# -----------------------
def opening_text(length: str, tone_style: str) -> str:
    if length == "1 minute":
        base = "Thank you for your speech today. I appreciate the effort you put into sharing your message."
    elif length == "2 minutes":
        base = "Thank you for your speech today. I appreciate the effort you put into preparing and delivering your message to the audience."
    else:
        base = "Thank you for your speech today. I enjoyed listening to your presentation and appreciate the effort you put into preparing and delivering your message."

    if tone_style == "Professional Mentor":
        return base.replace("I appreciate", "I recognise").replace("your message", "your purpose and message")
    if tone_style == "Neutral/Contest-Style":
        return "Thank you for your speech. Here is your evaluation based on observable criteria."
    return base

def closing_text(length: str, tone_style: str) -> str:
    if length == "1 minute":
        base = "Overall, this was a good effort, and I encourage you to keep practising."
    elif length == "2 minutes":
        base = "Overall, this was a solid speech with a strong foundation. With continued practice, your speeches will become even more impactful."
    else:
        base = "Overall, this was a strong speech with good potential. With more focus on refining your delivery and engaging the audience, your future speeches will continue to improve."

    if tone_style == "Professional Mentor":
        return base.replace("good potential", "strong potential").replace("keep practising", "keep refining your craft")
    if tone_style == "Neutral/Contest-Style":
        return "Overall, your speech met the general requirements. Continued refinement will improve impact and polish."
    return base

def pick_strengths_and_improvements(data: dict):
    strengths, improvements = [], []
    # Strength: 4–5, Improvement: 1–3
    for item in data.values():
        rt = int(item["rating"])
        if rt >= 4:
            strengths.append(item)
        else:
            improvements.append(item)

    strengths.sort(key=lambda x: x["rating"], reverse=True)
    improvements.sort(key=lambda x: x["rating"])
    return strengths, improvements

def one_line_point(item: dict, kind: str) -> str:
    title = item["title"]
    comment = item["comment"]
    if comment:
        if kind == "strength":
            return f"Your **{title}** stood out — {comment}"
        return f"For **{title}**, consider improving — {comment}"
    return f"{'Your **' + title + '** was a strength.' if kind == 'strength' else 'One area to improve is **' + title + '**.'}"

# -----------------------
# Generate Evaluation
# -----------------------
if st.button("Generate Evaluation"):
    if not rubric_data:
        st.warning("Please select at least one rubric criterion to score.")
        st.stop()

    strengths, improvements = pick_strengths_and_improvements(rubric_data)

    if evaluation_length == "1 minute":
        max_strengths, max_improve = 1, 1
    elif evaluation_length == "2 minutes":
        max_strengths, max_improve = 2, 2
    else:
        max_strengths, max_improve = 3, 2

    st.subheader("Rubric Summary")
    summary_rows = []
    for v in rubric_data.values():
        summary_rows.append({
            "Criterion": v["title"],
            "Rating": v["rating"],
            "Comment": v["comment"] if v["comment"] else "(no comment)"
        })
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    st.subheader("Structured Evaluation Preview")

    speaker_disp = speaker_name.strip() if speaker_name.strip() else "Speaker"
    title_disp = speech_title.strip()
    evaluator_disp = evaluator_name.strip() if evaluator_name.strip() else "Evaluator"

    pathway_line = ""
    if pathway != "---Please Select from this drop-down list--":
        pathway_line = f"This evaluation is aligned with the **{pathway}** pathway"
        if pathway_level != "---Please Select from this drop-down list--":
            pathway_line += f" (Level **{pathway_level}**)."
        else:
            pathway_line += "."

    st.markdown(f"""
### Opening
Thank you, **{speaker_disp}**, for your speech{f" titled *{title_disp}*" if title_disp else ""}.  
{pathway_line}  
{opening_text(evaluation_length, tone)}
""")

    st.markdown("### Commendations")
    if strengths:
        for s in strengths[:max_strengths]:
            st.write(f"- {one_line_point(s, 'strength')}")
    else:
        st.write("- You demonstrated good effort and confidence during your speech.")

    st.markdown("### Areas for Improvement")
    if improvements:
        for i in improvements[:max_improve]:
            st.write(f"- {one_line_point(i, 'improve')}")
    else:
        st.write("- Continue refining your delivery and audience engagement.")

    if notes.strip():
        st.markdown("### Notes You Captured (Optional)")
        st.write(notes.strip())

    st.markdown(f"""
### Encouraging Close
{closing_text(evaluation_length, tone)}

— *Evaluation by {evaluator_disp}*  
*Date: {meeting_date.strftime('%Y-%m-%d')}*
""")

    with st.expander("Copy/Paste Version", expanded=False):
        lines = []
        lines.append(f"OPENING: Thank you, {speaker_disp}, for your speech{(' titled ' + title_disp) if title_disp else ''}.")
        if pathway_line:
            lines.append(pathway_line.replace("**", ""))
        lines.append(opening_text(evaluation_length, tone))
        lines.append("")
        lines.append("COMMENDATIONS:")
        if strengths:
            for s in strengths[:max_strengths]:
                lines.append(f"- {one_line_point(s, 'strength').replace('**','')}")
        else:
            lines.append("- Good effort and confidence.")
        lines.append("")
        lines.append("AREAS FOR IMPROVEMENT:")
        if improvements:
            for i in improvements[:max_improve]:
                lines.append(f"- {one_line_point(i, 'improve').replace('**','')}")
        else:
            lines.append("- Continue refining delivery and engagement.")
        lines.append("")
        lines.append("CLOSE:")
        lines.append(closing_text(evaluation_length, tone))
        lines.append(f"— Evaluation by {evaluator_disp} ({meeting_date.strftime('%Y-%m-%d')})")
        st.code("\n".join(lines), language="text")
