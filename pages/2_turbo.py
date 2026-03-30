"""Turbo Usage Health Dashboard — Spreadsheet-style weekly view."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from services.data_processor import process_turbo_health, compute_turbo_trends

st.set_page_config(page_title="Turbo Health | Graas", page_icon="🔧", layout="wide")
st.markdown("## 🔧 Turbo — Weekly Usage Health Scores")

# ── Data Loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_turbo_data():
    csv_path = Path.home() / "Downloads" / "Pvt Beta Consolidated Insights - Usage Health Score.csv"
    if csv_path.exists():
        # Row 1 is "SUM of USAGESCORE,,,WEEK,,,..." (junk header)
        # Row 2 is the real header: ACCOUNT, DISPLAY_NAME, COUNTRY_CODE, 9 Mar, 2 Mar, ...
        return pd.read_csv(csv_path, header=1)
    return pd.DataFrame()

raw = load_turbo_data()

if raw.empty:
    st.warning("No Turbo data found. Please download the CSV from Google Sheets.")
    st.stop()

health = process_turbo_health(raw)
trends = compute_turbo_trends(health)

if health.empty:
    st.warning("Could not parse Turbo health data.")
    st.stop()

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

week_cols = [c for c in health.columns if c not in ("account_id", "display_name", "country")]

# ── Identify Top 50 and New Entrants ──────────────────────────────────────────

top50 = trends.sort_values("current_score", ascending=False).head(50)
top50_ids = top50["account_id"].tolist()

def detect_new_entrants(health_df, week_cols, recent_n=4, old_n=8):
    recent_cols = week_cols[:recent_n]
    old_cols = week_cols[recent_n:recent_n + old_n]
    new_ids = []
    for _, row in health_df.iterrows():
        recent_scores = [float(row[c]) for c in recent_cols]
        old_scores = [float(row[c]) for c in old_cols] if old_cols else []
        if any(s > 0 for s in recent_scores) and old_scores and all(s == 0 for s in old_scores):
            new_ids.append(row["account_id"])
    return new_ids

new_entrant_ids = detect_new_entrants(health, week_cols)
new_entrants = trends[trends["account_id"].isin(new_entrant_ids)].sort_values("current_score", ascending=False)

# ══════════════════════════════════════════════════════════════════════════════

tab_top50, tab_new = st.tabs([
    f"🏆 Top 50 Accounts",
    f"🆕 New Entrants ({len(new_entrants)})",
])


def render_weekly_grid(account_ids, num_weeks=12, key_prefix="grid"):
    """Render a spreadsheet-style weekly usage grid — the core view."""

    grid_data = health[health["account_id"].isin(account_ids)].copy()
    if grid_data.empty:
        st.info("No accounts to display.")
        return

    # Sort by most recent score descending
    first_week = week_cols[0]
    grid_data[first_week] = pd.to_numeric(grid_data[first_week], errors="coerce").fillna(0)
    grid_data = grid_data.sort_values(first_week, ascending=False)

    # Select columns to show
    show_weeks = week_cols[:num_weeks]
    display = grid_data[["display_name", "country"] + show_weeks].copy()
    display = display.reset_index(drop=True)
    display.insert(0, "#", range(1, len(display) + 1))
    display = display.rename(columns={"display_name": "Account", "country": "Ctry"})

    # Color coding function
    def color_cells(val):
        try:
            v = float(val)
        except (ValueError, TypeError):
            return ""
        if v >= 50:
            return "background-color: #065F46; color: white"
        elif v >= 40:
            return "background-color: #059669; color: white"
        elif v >= 30:
            return "background-color: #78350F; color: white"
        elif v > 0:
            return "background-color: #7F1D1D; color: white"
        else:
            return "background-color: #1a1a2e; color: #555"

    styled = display.style.applymap(color_cells, subset=show_weeks)

    st.dataframe(
        styled,
        use_container_width=True,
        height=min(800, 40 + len(display) * 35),
        hide_index=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: TOP 50
# ══════════════════════════════════════════════════════════════════════════════

with tab_top50:

    # Quick stats
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Avg Score", f"{top50['current_score'].mean():.0f}")
    with c2:
        st.metric("Healthy (70+)", int((top50["current_score"] >= 70).sum()))
    with c3:
        st.metric("Warning (30-69)", int(((top50["current_score"] >= 30) & (top50["current_score"] < 70)).sum()))
    with c4:
        st.metric("Declining", int((top50["trend"] == "declining").sum()), delta_color="inverse")

    # Filters
    col_country, col_weeks, col_search = st.columns([2, 2, 3])
    with col_country:
        countries = sorted(top50["country"].dropna().unique().tolist())
        sel_countries = st.multiselect("Country", countries, default=countries, key="t50_ctry")
    with col_weeks:
        num_weeks = st.slider("Weeks to show", 4, min(len(week_cols), 26), 12, key="t50_weeks")
    with col_search:
        search = st.text_input("Search account", "", key="t50_search")

    # Filter accounts
    filtered_ids = top50[top50["country"].isin(sel_countries)]["account_id"].tolist()
    if search:
        match = health[health["display_name"].str.contains(search, case=False, na=False)]["account_id"].tolist()
        filtered_ids = [aid for aid in filtered_ids if aid in match]

    # ── The main spreadsheet grid ─────────────────────────────────────────────
    st.markdown("### Weekly Usage Scores")
    st.caption("🟢 70+ Healthy | 🟠 50-69 Moderate | 🟤 30-49 Warning | 🔴 <30 At Risk | ⚫ 0 Inactive")
    render_weekly_grid(filtered_ids, num_weeks=num_weeks, key_prefix="t50")

    # ── WoW change sparklines ─────────────────────────────────────────────────
    st.markdown("### Week-over-Week Changes")

    wow_data = top50[["display_name", "current_score", "prev_score", "change", "trend"]].copy()
    wow_data["trend_icon"] = wow_data["trend"].map({"improving": "📈", "stable": "➡️", "declining": "📉"})
    wow_data["trend_display"] = wow_data["trend_icon"] + " " + wow_data["trend"]
    wow_data = wow_data.sort_values("change", ascending=False)

    st.dataframe(
        wow_data[["display_name", "current_score", "prev_score", "change", "trend_display"]]
        .rename(columns={
            "display_name": "Account", "current_score": "This Week",
            "prev_score": "Last Week", "change": "Change", "trend_display": "Trend",
        }),
        use_container_width=True, hide_index=True, height=400,
    )

    # ── Account deep-dive chart ───────────────────────────────────────────────
    st.markdown("### Account Deep-Dive")
    names = health[health["account_id"].isin(top50_ids)]["display_name"].sort_values().tolist()
    selected = st.selectbox("Select Account", names, key="t50_dd")
    if selected:
        row = health[health["display_name"] == selected].iloc[0]
        scores = [float(row[c]) for c in week_cols]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=week_cols, y=scores, mode="lines+markers",
            line=dict(color="#4F46E5", width=2),
            fill="tozeroy", fillcolor="rgba(79, 70, 229, 0.1)",
        ))
        fig.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="At Risk")
        fig.add_hline(y=70, line_dash="dash", line_color="green", annotation_text="Healthy")
        fig.update_layout(
            height=350, template="plotly_dark",
            xaxis_title="Week", yaxis_title="Health Score",
            yaxis_range=[0, 105], margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: NEW ENTRANTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_new:
    st.markdown("Accounts active in last 4 weeks that were inactive in the 8 weeks before")

    if new_entrants.empty:
        st.info("No new entrants detected in the current period.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("New Entrants", len(new_entrants))
        with c2:
            st.metric("Avg Score", f"{new_entrants['current_score'].mean():.0f}")
        with c3:
            top_ctry = new_entrants["country"].value_counts()
            st.metric("Top Country", f"{top_ctry.index[0]} ({top_ctry.iloc[0]})" if len(top_ctry) > 0 else "N/A")

        # Weeks slider for new entrants
        ne_weeks = st.slider("Weeks to show", 4, min(len(week_cols), 20), 16, key="ne_weeks")

        # ── Spreadsheet grid for new entrants ─────────────────────────────────
        st.markdown("### Weekly Usage Scores — Ramp Up")
        st.caption("🟢 70+ Healthy | 🟠 50-69 Moderate | 🟤 30-49 Warning | 🔴 <30 At Risk | ⚫ 0 Inactive")
        render_weekly_grid(new_entrant_ids, num_weeks=ne_weeks, key_prefix="ne")

        # Deep-dive
        st.markdown("### Account Deep-Dive")
        ne_names = health[health["account_id"].isin(new_entrant_ids)]["display_name"].sort_values().tolist()
        ne_selected = st.selectbox("Select Account", ne_names, key="ne_dd")
        if ne_selected:
            row = health[health["display_name"] == ne_selected].iloc[0]
            scores = [float(row[c]) for c in week_cols[:ne_weeks]]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=week_cols[:ne_weeks], y=scores, mode="lines+markers",
                line=dict(color="#10B981", width=2),
                fill="tozeroy", fillcolor="rgba(16, 185, 129, 0.1)",
            ))
            fig.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="At Risk")
            fig.add_hline(y=70, line_dash="dash", line_color="green", annotation_text="Healthy")
            fig.update_layout(
                height=350, template="plotly_dark",
                xaxis_title="Week", yaxis_title="Health Score",
                yaxis_range=[0, 105], margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
