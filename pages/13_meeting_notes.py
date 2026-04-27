"""Meeting Notes Store — Slack-extracted notes with persistent storage."""

import streamlit as st
from services.notes_store import get_all_notes, save_from_slack

st.set_page_config(page_title="Meeting Notes | Graas", page_icon="📝", layout="wide")
st.markdown("## 📝 Meeting Notes Store")
st.caption("Pulled from Slack GTM channels — persisted locally for history")

tab_stored, tab_pull = st.tabs(["📚 All Stored Notes", "💬 Pull from Slack"])

# ── Tab: All Stored Notes ────────────────────────────────────────────────────

with tab_stored:
    notes = get_all_notes()
    if not notes:
        st.info("No notes stored yet. Go to the 'Pull from Slack' tab to fetch notes.")
    else:
        missing = [n for n in notes if n.get("missing_granola")]
        with_notes = [n for n in notes if not n.get("missing_granola")]
        st.success(f"{len(notes)} meeting note(s) stored")

        if missing:
            st.warning(f"⚠️ **{len(missing)} meeting(s) without Granola notes**")
            for n in missing:
                st.markdown(f"- **{n['client']}** — {n['date']} — {n.get('author', '')} ({n.get('channel', '')})")
            st.markdown("---")

        for note in notes:
            takeaway_count = len(note.get("takeaways", []))
            if note.get("missing_granola"):
                icon = "⚠️"
                flag = " — **NO GRANOLA NOTES**"
            else:
                icon = "📋"
                flag = ""

            label = f"{icon} **{note['client']}** — {note['date']}"
            if note.get("author"):
                label += f" — {note['author']}"
            if takeaway_count:
                label += f" — {takeaway_count} point(s)"
            label += flag

            with st.expander(label):
                if note.get("missing_granola"):
                    st.error("No Granola notes shared for this meeting. Please follow up with the attendee.")
                if note.get("summary"):
                    st.markdown(note["summary"])
                    st.markdown("---")
                if note.get("takeaways"):
                    for t in note["takeaways"]:
                        st.markdown(f"- {t}")
                if note.get("granola"):
                    st.markdown(f"[Open in Granola]({note['granola']})")
                st.caption(f"Source: {note.get('source', 'unknown')} | Stored: {note.get('stored_at', '—')[:10]}")

# ── Tab: Pull from Slack ─────────────────────────────────────────────────────

with tab_pull:
    st.markdown("### 💬 Pull & Store from Slack")
    st.caption("Fetches meeting notes from `#ebu-offerings-gtm` and `#my-gtm-alle`, then persists them locally.")

    col1, col2 = st.columns([1, 3])
    with col1:
        lookback = st.number_input("Lookback (days)", min_value=7, max_value=90, value=30)

    if st.button("🔄 Pull from Slack & Save", key="slack_pull"):
        with st.spinner("Fetching from Slack..."):
            try:
                from services.slack_notes import fetch_meeting_notes
                slack_notes = fetch_meeting_notes(lookback_days=lookback)
                if slack_notes:
                    added = save_from_slack(slack_notes)
                    missing = sum(1 for n in slack_notes if n.get("missing_granola"))
                    st.success(f"Fetched {len(slack_notes)} note(s) from Slack. **{added} new** added to store.")
                    if missing:
                        st.warning(f"⚠️ {missing} meeting(s) have no Granola notes attached")

                    for note in slack_notes[:10]:
                        icon = "⚠️" if note.get("missing_granola") else "📋"
                        with st.expander(f"{icon} {note['client']} — {note['date']}"):
                            if note.get("missing_granola"):
                                st.error("No Granola notes for this meeting")
                            if note.get("summary"):
                                st.markdown(note["summary"])
                                st.markdown("---")
                            if note["takeaways"]:
                                for t in note["takeaways"]:
                                    st.markdown(f"- {t}")
                            else:
                                st.caption("No takeaways extracted")
                            if note.get("granola"):
                                st.markdown(f"[Granola link]({note['granola']})")
                else:
                    st.warning("No meeting notes found in Slack. Is `SLACK_BOT_TOKEN` configured?")
            except Exception as e:
                st.error(f"Failed to fetch from Slack: {e}")
