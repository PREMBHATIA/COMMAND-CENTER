"""Graas Product & Ops Dashboard — Hoppr, Turbo, Execute."""

import streamlit as st

st.set_page_config(
    page_title="Graas Product & Ops",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">Graas Product & Ops Dashboard</p>', unsafe_allow_html=True)
st.markdown("Hoppr usage, Turbo health scores, and Execute engineering tracker")

st.markdown("---")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### 📊 Hoppr")
    st.markdown("Daily usage, funnel, key accounts, query analysis")
    st.page_link("pages/1_hoppr.py", label="Open →")
with c2:
    st.markdown("### 🔧 Turbo")
    st.markdown("Top 50 health scores, new entrants")
    st.page_link("pages/2_turbo.py", label="Open →")
with c3:
    st.markdown("### ⚙️ Execute")
    st.markdown("Sprint stories, infra costs, support issues")
    st.page_link("pages/3_execute.py", label="Open →")
