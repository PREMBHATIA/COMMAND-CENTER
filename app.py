"""Graas Command Center — Unified Monitoring Dashboard."""

import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Graas Command Center",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #9CA3AF;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background: #1E1E2E;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #2D2D3F;
    }
    .stMetric label { font-size: 0.85rem !important; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🎯 Graas Command Center")
    st.markdown("---")
    st.markdown("**Products**")
    st.markdown("- 📊 Hoppr — AI Analytics")
    st.markdown("- 🔧 Turbo — Platform Health")
    st.markdown("- 💰 Finance — P&L & AR")
    st.markdown("- 📋 Pipeline — Proposals")
    st.markdown("- 🌿 All-e: PI Mitra Connect")
    st.markdown("- 🔍 Competitors — Intel Feed")
    st.markdown("- 💬 Ask Graas — AI Chat")
    st.markdown("---")
    st.markdown("**Quick Links**")
    st.markdown("[Hoppr Sheet](https://docs.google.com/spreadsheets/d/1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM/)")
    st.markdown("[Turbo Sheet](https://docs.google.com/spreadsheets/d/1L1FJ-MXCB4sjCJbHR8SkSrvkrBpSLUWwrBZ58Wcpv0Q/)")
    st.markdown("[Finance P&L](https://docs.google.com/spreadsheets/d/1njRsoDj5QVh__Nq1cHZ8lYMMEJA28_oj/)")
    st.markdown("[SaaS Revenue Tracker](https://docs.google.com/spreadsheets/d/1iytl7KYQVa-7XC6vpoHmDBE14pV5zCgKH5-w3V4rFlI/)")

# Main content
st.markdown('<p class="main-header">Graas Command Center</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Unified monitoring across Products, Sales & Finance</p>', unsafe_allow_html=True)

# Check data availability
csv_dir = Path(__file__).parent / "data" / "cache"
has_csv = any(csv_dir.glob("*.parquet")) if csv_dir.exists() else False

col1, col2, col3, col4 = st.columns(4)
col5, col6, col7, col8 = st.columns(4)

with col1:
    st.markdown("### 📊 Hoppr")
    st.markdown("Product usage analytics")
    st.page_link("pages/1_hoppr.py", label="Open Dashboard →")

with col2:
    st.markdown("### 🔧 Turbo")
    st.markdown("Usage health scores")
    st.page_link("pages/2_turbo.py", label="Open Dashboard →")

with col3:
    st.markdown("### 💰 Finance")
    st.markdown("P&L & Invoicing")
    st.page_link("pages/3_finance.py", label="Open Dashboard →")

with col4:
    st.markdown("### 📋 Pipeline")
    st.markdown("Proposals tracker")
    st.page_link("pages/4_pipeline.py", label="Open Dashboard →")

with col5:
    st.markdown("### 🌿 PI Mitra")
    st.markdown("All-e dealer ordering")
    st.page_link("pages/5_pi_mitra.py", label="Open Dashboard →")

with col6:
    st.markdown("### 🔍 Competitors")
    st.markdown("Intel feed")
    st.page_link("pages/7_competitors.py", label="Open Dashboard →")

with col7:
    st.markdown("### 🤖 All-e")
    st.markdown("Presales pipeline")
    st.page_link("pages/8_alle.py", label="Open Dashboard →")

with col8:
    st.markdown("### 💬 Ask Graas")
    st.markdown("AI-powered Q&A")
    st.page_link("pages/10_ask_graas.py", label="Ask a Question →")

st.markdown("---")

# Data source status
st.markdown("### Data Sources")

sources = [
    ("Hoppr Dashboard", "Google Sheet", "hoppr Dashboard - Hoppr__Anaysis.csv"),
    ("Turbo Health Scores", "Google Sheet", "Pvt Beta Consolidated Insights - Usage Health Score.csv"),
    ("AOP Revenue Tracker", "Google Sheet", "Weekly Revenue Call - Key Metrics Tracking - AOP -2026.csv"),
    ("PI Mitra Connect", "Google Sheet", None),
    ("Graas.ai Visitors", "Looker Studio", None),
]

downloads_dir = Path.home() / "Downloads"

for name, source_type, csv_file in sources:
    col_name, col_type, col_status = st.columns([3, 2, 2])
    with col_name:
        st.markdown(f"**{name}**")
    with col_type:
        st.markdown(f"`{source_type}`")
    with col_status:
        if csv_file and (downloads_dir / csv_file).exists():
            st.markdown("✅ CSV Available")
        elif has_csv:
            st.markdown("✅ Cached")
        else:
            st.markdown("⏳ Not loaded")

st.markdown("---")
st.markdown("💡 **Tip:** Use `← sidebar` to navigate between dashboards, or click the links above.")
