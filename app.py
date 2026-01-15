import streamlit as st
from datetime import date

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
# Basic info
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
                "Effective Coaching",
                "Innovative Planning",
                "Leadership Development",
                "Strategic Relationships",
                "Team Collaboration"
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
# Rubric definition (PARAPHRASED level guides)
# -----------------------
RATING_LABELS = {
    5: "5 — Exemplary",
    4: "4 — Excels",
    3: "3 — Accomplished",
    2: "2 — Emerging",
    1: "1 — Developing",
}

RUBRICS = [
    {
        "key": "clarity",
        "title": "Clarity",
        "desc": "Spoken language is clear and easily understood.",
        "levels": {
            5: "Consistently crystal-clear; effortless to follow.",
            4: "Very clear overall; strong word choice and phrasing.",
            3: "Generally clear and understandable.",
            2: "Sometimes unclear or hard to follow; needs refinement.",
            1: "Often unclear; meaning is difficult to understand.",
        },
    },
    {
        "key": "vocal_variety",
        "title": "Vocal Variety",
        "desc": "Uses tone, speed, and volume as tools.",
        "levels": {
            5: "Voice choices feel intentional and polished throughout.",
            4: "Good variation; voice supports meaning effectively.",
            3: "Some variation; can be more intentional/consistent.",
            2: "Limited variation; needs practice with emphasis and pace.",
            1: "Mostly flat/ineffective variation; hard to stay engaged.",
        },
    },
    {
        "key": "eye_contact",
        "title": "Eye Contact",
        "desc": "Uses eye contact to engage the audience.",
        "levels": {
            5: "Strong connection; eye contact supports emotion and impact.",
            4: "Frequent eye contact; checks in with audience well.",
            3: "Adequate eye contact; engagement is present but can improve.",
            2: "Inconsistent eye contact; connection drops at times.",
            1: "Minimal eye contact; reads/looks away most of the time.",
        },
    },
    {
        "key": "gestures",
        "title": "Gestures",
        "desc": "Uses physical gestures effectively.",
        "levels": {
            5: "Gestures consistently enhance meaning and delivery.",
            4: "Gestures support key points; mostly natural and effective.",
            3: "Some effective gestures; could be clearer/more consistent.",
            2: "Gestures distract or feel limited; needs practice.",
            1: "Few/no gestures or distracting gestures; reduces impact.",
        },
    },
    {
        "key": "audience_awareness",
        "title": "Audience Awareness",
        "desc": "Shows awareness of audience engagement and needs.",
        "levels": {
            5: "Anticipates audience needs; adjusts smoothly and confidently.",
            4: "Aware of audience response; adapts effectively.",
            3: "Shows awareness of engagement; occasional adjustment.",
            2: "Engagement awareness needs practice; limited adaptation.",
            1: "Little attempt to engage or meet audience needs.",
        },
    },
    {
        "key": "comfort_level",
        "title": "Comfort Level",
        "desc": "Appears comfortable with the audience.",
        "levels": {
            5: "Highly confident and at ease throughout.",
            4: "Comfortable and steady; minor nerves don’t distract.",
            3: "Generally comfortable; a few tense moments.",
            2: "Noticeable discomfort; affects delivery.",
            1: "Highly uncomfortable; significantly reduces engagement.",
        },
    },
    {
        "key": "interest",
        "title": "Interest",
        "desc": "Engages the audience with interesting, well-constructed content.",
        "levels": {
            5: "Very compelling; holds attention strongly from start to end.",
            4: "Engaging and well-structured; audience stays interested.",
            3: "Interesting overall; could be tighter or more vivid.",
            2: "Somewhat interesting; structure/detail needs improvement.",
            1: "Low interest; content feels unclear or unengaging.",
        },
    },
    {
        "key": "well_supported",
        "title": "Well Supported",
        "desc": "Content is supported; sources/examples are credible when needed.",
        "levels": {
            5: "Strong support (examples/facts) that clearly strengthens message.",
            4: "Good support; details back up the main points well.",
            3: "Some support; could add stronger evidence or examples.",
            2: "Support is weak/unclear; needs better evidence/examples.",
            1: "Little/no support; claims feel disconnected or ungrounded.",
        },
    },
]

# -----------------------
# Controls
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
# Helper functions
# -----------------------
def opening_text(length: str, tone_style: str) -> str:
    if tone_style == "Neutral/Contest-Style":
        return "Thank you for your speech. Here is your evaluation based on observable criteria."
    if length == "1 minute":
        base = "Thank you for your speech today. I appreciate the effort you put into sharing your message."
    elif length == "2 minutes":
        base = "Thank you for your speech today. I appreciate the effort you put into preparing and delivering your message to the audience."
    else:
        base = "Thank you for your speech today. I enjoyed listening to your presentation and appreciate the effort you put into preparing and delivering your message."
    if tone_style == "Professional Mentor":
        base = base.replace("I appreciate", "I recognise").replace("your message", "your purpose and message")
    return base

def closing_text(length: str, tone_style: str) -> str:
    if tone_style == "Neutral/Contest-Style":
        return "Overall, your speech met the general requirements. Continued refinement will improve impact and polish."
    if length == "1 minute":
        base = "Overall, this was a good effort, and I encourage you to keep practising."
    elif length == "2 minutes":
        base = "Overall, this was a solid speech with a strong foundation. With continued practice, your speeches will become even more impactful."
    else:
        base = "Overall, this was a strong speech with good potential. With more focus on refining your delivery and engaging the audience, your future speeches will continue to improve."
    if tone_style == "Professional Mentor":
        base = base.replace("keep practising", "keep refining your craft")
    return base

def pick_strengths_and_improvements(data: dict):
    strengths, improvements = [], []
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
            return f"Your {title} stood out — {comment}"
        return f"For {title}, consider improving — {comment}"
    level_hint = item.get("level_hint", "")
    if level_hint:
        if kind == "strength":
            return f"Your {title} was strong ({level_hint})."
        return f"To improve {title}, aim for the next level ({level_hint})."
    return f"{'Your ' + title + ' was a strength.' if kind == 'strength' else 'One area to improve is ' + title + '.'}"

def default_bullets(items: list, kind: str, limit: int):
    if not items:
        return ""
    return "\n".join([f"- {one_line_point(it, kind)}" for it in items[:limit]])

def ensure_state(key: str, value: str):
    if key not in st.session_state:
        st.session_state[key] = value

def safe_md(text: str) -> str:
    return text.strip() if text and text.strip() else "- (No input provided.)"

# -----------------------
# Rubric scoring UI
# -----------------------
st.subheader("Rubric Scoring (1–5) + Comments")
st.caption("Each rubric shows a short 1–5 guide (paraphrased) to help you score consistently.")

rubric_data = {}
for r in RUBRICS:
    if r["title"] not in focus:
        continue

    left, right = st.columns([2.2, 1.2])

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

        selected_desc = r["levels"].get(int(rating), "")
        if selected_desc:
            st.caption(f"Selected level: {selected_desc}")

        with st.expander("Show 1–5 scoring guide", expanded=False):
            for lvl in [5, 4, 3, 2, 1]:
                st.write(f"**{lvl}** — {r['levels'][lvl]}")

    with right:
        comment = st.text_area(
            "Comment (optional)",
            placeholder="One concrete example (what you observed).",
            height=92,
            key=f"comment_{r['key']}",
        )

    rubric_data[r["key"]] = {
        "title": r["title"],
        "rating": int(rating),
        "comment": comment.strip(),
        "level_hint": selected_desc
    }

st.divider()

# -----------------------
# General Comments
# -----------------------
st.subheader("General Comments")
st.caption("These boxes auto-fill from your rubric selections. Edit freely.")

if evaluation_length == "1 minute":
    max_strengths, max_improve = 1, 1
elif evaluation_length == "2 minutes":
    max_strengths, max_improve = 2, 2
else:
    max_strengths, max_improve = 3, 2

strengths_now, improvements_now = pick_strengths_and_improvements(rubric_data) if rubric_data else ([], [])
suggest_excelled = default_bullets(strengths_now, "strength", max_strengths)
suggest_workon = default_bullets(improvements_now, "improve", max_improve)

if improvements_now:
    ch = improvements_now[0]
    suggest_challenge = f"- To challenge yourself, focus on **{ch['title']}** next time. Try one drill and check improvement."
else:
    selected_titles = [r["title"] for r in RUBRICS if r["title"] in focus]
    suggest_challenge = f"- To challenge yourself, choose one focus area next time: **{selected_titles[0]}**." if selected_titles else "- To challenge yourself, pick one key focus area for your next speech."

ensure_state("gc_excelled", suggest_excelled)
ensure_state("gc_workon", suggest_workon)
ensure_state("gc_challenge", suggest_challenge)

cX, _ = st.columns([1, 3])
with cX:
    if st.button("Auto-fill from rubric"):
        st.session_state["gc_excelled"] = suggest_excelled
        st.session_state["gc_workon"] = suggest_workon
        st.session_state["gc_challenge"] = suggest_challenge

excelled_at = st.text_area("You excelled at:", key="gc_excelled", height=110, placeholder="- Clarity\n- Eye contact\n- Vocal variety")
work_on = st.text_area("You may want to work on:", key="gc_workon", height=110, placeholder="- One key improvement\n- One practice tip")
challenge_yourself = st.text_area("To challenge yourself:", key="gc_challenge", height=90, placeholder="- One stretch goal for the next speech")

st.divider()

# -----------------------
# Generate output
# -----------------------
if st.button("Generate Evaluation"):
    if not rubric_data:
        st.warning("Please select at least one rubric criterion to score.")
        st.stop()

    strengths, improvements = pick_strengths_and_improvements(rubric_data)

    st.subheader("Rubric Summary")
    summary_rows = []
    for v in rubric_data.values():
        summary_rows.append({
            "Criterion": v["title"],
            "Rating": v["rating"],
            "Guide (selected level)": v["level_hint"],
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

    excelled_text = safe_md(excelled_at) if excelled_at.strip() else (default_bullets(strengths, "strength", max_strengths) or "- You demonstrated good effort and confidence.")
    workon_text = safe_md(work_on) if work_on.strip() else (default_bullets(improvements, "improve", max_improve) or "- Continue refining your delivery and audience engagement.")
    challenge_text = safe_md(challenge_yourself) if challenge_yourself.strip() else safe_md(suggest_challenge)

    st.markdown("### You excelled at:")
    st.markdown(excelled_text)

    st.markdown("### You may want to work on:")
    st.markdown(workon_text)

    st.markdown("### To challenge yourself:")
    st.markdown(challenge_text)

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
        lines.append("YOU EXCELLED AT:")
        lines.append(excelled_text.replace("**", ""))
        lines.append("")
        lines.append("YOU MAY WANT TO WORK ON:")
        lines.append(workon_text.replace("**", ""))
        lines.append("")
        lines.append("TO CHALLENGE YOURSELF:")
        lines.append(challenge_text.replace("**", ""))
        lines.append("")
        lines.append("CLOSE:")
        lines.append(closing_text(evaluation_length, tone))
        lines.append(f"— Evaluation by {evaluator_disp} ({meeting_date.strftime('%Y-%m-%d')})")
        st.code("\n".join(lines), language="text")
