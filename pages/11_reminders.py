"""Weekly Team Updates & Reminders."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Reminders | Graas", page_icon="📋", layout="wide")
st.markdown("## 📋 Weekly Team Updates & Reminders")
st.markdown("Track team PPT updates and key review items")

# ── Team Update Sources ───────────────────────────────────────────────────────

st.markdown("### Team Update Decks")

team_updates = [
    {
        "team": "Agent Foundry",
        "type": "PPT",
        "link": "https://docs.google.com/presentation/d/1i2hAFuwmSNvRDOmakJkAPnwzewBp-AGu20olfHAlwwU/edit",
        "icon": "🤖",
        "description": "Weekly product & engineering updates",
        "review_day": "Monday",
    },
    {
        "team": "BUA (Business Unit Analytics)",
        "type": "Sheet",
        "link": "https://docs.google.com/spreadsheets/d/1sQWIVALRnaR2BNWiPaqt6sAyGQWVwC47gmyuxndy-U4/edit",
        "icon": "📊",
        "description": "Business unit metrics & analytics",
        "review_day": "Monday",
    },
    {
        "team": "Turbo Execute",
        "type": "PPT",
        "link": "https://docs.google.com/presentation/d/1mWzpiiKM-or1NJJXOheL_9cE05bfHZhxnagr8AC_kkQ/edit",
        "icon": "🔧",
        "description": "Turbo execution updates & blockers",
        "review_day": "Monday",
    },
]

# Show current day context
today = datetime.now()
day_name = today.strftime("%A")
st.caption(f"Today is **{day_name}, {today.strftime('%B %d, %Y')}**")

# Review status tracking (persisted in session state)
if "review_status" not in st.session_state:
    st.session_state.review_status = {}

week_key = today.strftime("%Y-W%U")

for update in team_updates:
    team = update["team"]
    status_key = f"{week_key}_{team}"
    reviewed = st.session_state.review_status.get(status_key, False)

    col_icon, col_info, col_link, col_status = st.columns([1, 5, 2, 2])

    with col_icon:
        st.markdown(f"### {update['icon']}")
    with col_info:
        st.markdown(f"**{update['team']}**")
        st.caption(f"{update['description']} | Review: {update['review_day']}")
    with col_link:
        st.markdown(f"[Open {update['type']} →]({update['link']})")
    with col_status:
        if st.checkbox("Reviewed", value=reviewed, key=status_key):
            st.session_state.review_status[status_key] = True
        else:
            st.session_state.review_status[status_key] = False

st.markdown("---")

# ── Weekly Checklist ──────────────────────────────────────────────────────────

st.markdown("### Weekly Review Checklist")

checklist_items = [
    ("Review Agent Foundry deck for product updates", "Monday"),
    ("Check BUA metrics sheet for anomalies", "Monday"),
    ("Review Turbo Execute deck for blockers", "Monday"),
    ("Check Hoppr usage trends (WoW changes)", "Tuesday"),
    ("Review Turbo health scores — flag at-risk accounts", "Tuesday"),
    ("Review AOP revenue tracker — Q1 achievement", "Wednesday"),
    ("Check competitor intel feed for new alerts", "Wednesday"),
    ("Review PI Mitra Connect analytics", "Thursday"),
    ("Prepare weekly summary for leadership", "Friday"),
]

if "checklist" not in st.session_state:
    st.session_state.checklist = {}

for item_text, day in checklist_items:
    item_key = f"{week_key}_{item_text[:30]}"
    is_today = day == day_name

    col_check, col_item, col_day = st.columns([1, 8, 2])
    with col_check:
        checked = st.checkbox(
            "", value=st.session_state.checklist.get(item_key, False),
            key=item_key, label_visibility="collapsed",
        )
        st.session_state.checklist[item_key] = checked
    with col_item:
        if checked:
            st.markdown(f"~~{item_text}~~")
        elif is_today:
            st.markdown(f"**{item_text}** 👈")
        else:
            st.markdown(item_text)
    with col_day:
        if is_today:
            st.markdown(f"**{day}** (today)")
        else:
            st.markdown(day)

# ── Notes ─────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Quick Notes")

if "weekly_notes" not in st.session_state:
    st.session_state.weekly_notes = ""

notes = st.text_area(
    "Notes for this week",
    value=st.session_state.weekly_notes,
    height=150,
    key="notes_input",
    placeholder="Jot down key takeaways, action items, or things to follow up on...",
)
st.session_state.weekly_notes = notes

# ── Progress ──────────────────────────────────────────────────────────────────

st.markdown("---")
total = len(checklist_items)
completed = sum(1 for item_text, _ in checklist_items
                if st.session_state.checklist.get(f"{week_key}_{item_text[:30]}", False))

st.progress(completed / total if total > 0 else 0)
st.caption(f"**{completed}/{total}** items completed this week")
