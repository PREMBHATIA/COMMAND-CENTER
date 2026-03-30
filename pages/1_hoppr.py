"""Hoppr Usage Dashboard — Funnel, Key Accounts, Interesting Queries."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
from services.data_processor import process_hoppr_daily, process_hoppr_country, compute_hoppr_wow, detect_anomalies

st.set_page_config(page_title="Hoppr Usage | Graas", page_icon="📊", layout="wide")
st.markdown("## 📊 Hoppr Dashboard")

# ── Data Loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_hoppr_daily():
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Hoppr__Anaysis.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_funnel():
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Final Funnel.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, header=None)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_daily_analytics():
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Daily Analytics - Rohan.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, header=None)
    return pd.DataFrame()

raw_daily = load_hoppr_daily()
raw_funnel = load_funnel()
raw_analytics = load_daily_analytics()

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Process daily data
daily = process_hoppr_daily(raw_daily) if not raw_daily.empty else pd.DataFrame()
country = process_hoppr_country(raw_daily) if not raw_daily.empty else pd.DataFrame()

# ══════════════════════════════════════════════════════════════════════════════

tab_funnel, tab_accounts, tab_queries = st.tabs([
    "🔄 Funnel",
    "👥 Key Accounts",
    "💬 Interesting Queries",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: FUNNEL
# ══════════════════════════════════════════════════════════════════════════════

with tab_funnel:

    # ── Daily Usage Trends (TOP) ──────────────────────────────────────────────

    if not daily.empty:
        st.markdown("### Daily Usage Trends")

        # KPI cards — this week vs last week
        today = daily["date"].max()
        this_week = daily[daily["date"] >= today - pd.Timedelta(days=7)]
        last_week = daily[(daily["date"] >= today - pd.Timedelta(days=14)) &
                          (daily["date"] < today - pd.Timedelta(days=7))]

        def safe_delta(tw, lw):
            if lw == 0:
                return None
            return f"{((tw - lw) / lw * 100):+.0f}%"

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            tw_q = this_week["total_queries"].sum()
            lw_q = last_week["total_queries"].sum()
            st.metric("Queries (7d)", f"{tw_q:,}", safe_delta(tw_q, lw_q))
        with c2:
            tw_u = this_week["unique_users"].sum()
            lw_u = last_week["unique_users"].sum()
            st.metric("Unique Users (7d)", f"{tw_u:,}", safe_delta(tw_u, lw_u))
        with c3:
            tw_s = this_week["unique_sellers"].sum()
            lw_s = last_week["unique_sellers"].sum()
            st.metric("Unique Sellers (7d)", f"{tw_s:,}", safe_delta(tw_s, lw_s))
        with c4:
            tw_n = this_week["new_signups"].sum()
            lw_n = last_week["new_signups"].sum()
            st.metric("New Signups (7d)", f"{tw_n:,}", safe_delta(tw_n, lw_n))

        # Date range filter
        date_range = st.date_input(
            "Date Range",
            value=(daily["date"].min().date(), daily["date"].max().date()),
            key="hoppr_dates",
        )
        if len(date_range) == 2:
            mask = (daily["date"].dt.date >= date_range[0]) & (daily["date"].dt.date <= date_range[1])
            daily_f = daily[mask]
        else:
            daily_f = daily

        # Main trend chart
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=daily_f["date"], y=daily_f["total_queries"],
                                       mode="lines+markers", name="Queries", line=dict(color="#4F46E5", width=2)))
        fig_trend.add_trace(go.Bar(x=daily_f["date"], y=daily_f["unique_sellers"],
                                    name="Unique Sellers", marker_color="#7C3AED", opacity=0.5))
        fig_trend.add_trace(go.Scatter(x=daily_f["date"], y=daily_f["new_signups"],
                                       mode="lines+markers", name="New Signups",
                                       line=dict(color="#10B981", dash="dot")))
        fig_trend.update_layout(height=380, template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_trend, use_container_width=True)

        # Country breakdown
        if not country.empty:
            st.markdown("### By Country")
            ca = country.groupby("country").agg({"total_queries": "sum", "unique_sellers": "sum"}).reset_index()
            ca = ca[ca["country"] != "Unknown"].sort_values("total_queries", ascending=True)
            fig_c = px.bar(ca, x="total_queries", y="country", orientation="h",
                           color_discrete_sequence=["#4F46E5"])
            fig_c.update_layout(height=250, template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_c, use_container_width=True)

        # WoW table
        wow = compute_hoppr_wow(daily_f)
        if not wow.empty and len(wow) > 1:
            with st.expander("📋 Week-over-Week Data"):
                st.dataframe(
                    wow[["year", "week", "total_queries", "total_queries_wow",
                         "unique_users", "unique_users_wow",
                         "unique_sellers", "unique_sellers_wow"]].tail(10).style.format({
                        "total_queries_wow": "{:+.1f}%",
                        "unique_users_wow": "{:+.1f}%",
                        "unique_sellers_wow": "{:+.1f}%",
                    }),
                    use_container_width=True,
                )
    else:
        st.warning("No daily data. Download the 'Hoppr__Anaysis' tab from the Hoppr sheet.")

    # ── Funnel (BELOW) ────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### Acquisition Funnel")

    if not raw_funnel.empty:
        def safe_int(df, r, c):
            try:
                val = str(df.iloc[r, c]).replace(",", "").replace("₹", "").strip()
                return int(float(val))
            except:
                return 0

        chat_visits = safe_int(raw_funnel, 1, 7)
        unique_users = safe_int(raw_funnel, 4, 8)
        signups = safe_int(raw_funnel, 9, 7)
        connect_flow = safe_int(raw_funnel, 13, 6)
        connected = safe_int(raw_funnel, 17, 5)

        funnel_stages = ["Chat Visits", "Unique Users", "Signups", "Connect Flow", "Connected"]
        funnel_values = [chat_visits, unique_users, signups, connect_flow, connected]
        filtered_stages = [(s, v) for s, v in zip(funnel_stages, funnel_values) if v > 0]

        if filtered_stages:
            stages, values = zip(*filtered_stages)

            fig_funnel = go.Figure(go.Funnel(
                y=list(stages),
                x=list(values),
                textinfo="value+percent initial+percent previous",
                marker=dict(color=["#4F46E5", "#6366F1", "#7C3AED", "#8B5CF6", "#10B981"]),
                connector=dict(line=dict(color="#374151", width=2)),
            ))
            fig_funnel.update_layout(
                height=380, template="plotly_dark",
                margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(fig_funnel, use_container_width=True)

        # Funnel KPI row
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Chat Visits", f"{chat_visits:,}")
        with c2:
            st.metric("Unique Users", f"{unique_users:,}")
        with c3:
            st.metric("Signups", f"{signups:,}")
        with c4:
            conv = f"{connect_flow/signups*100:.0f}%" if signups > 0 else "N/A"
            st.metric("Connect Flow", f"{connect_flow:,}")
            st.caption(f"Signup → Connect: {conv}")
        with c5:
            conv2 = f"{connected/connect_flow*100:.0f}%" if connect_flow > 0 else "N/A"
            st.metric("Connected", f"{connected:,}")
            st.caption(f"Connect → Done: {conv2}")
    else:
        st.info("No funnel data. Download the 'Final Funnel' tab from the Hoppr sheet.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: KEY ACCOUNTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_accounts:
    st.markdown("### Key Account Usage")

    if raw_analytics.empty:
        st.warning("No account data. Download the 'Daily Analytics' tab from the Hoppr sheet.")
    else:
        # Parse the seller report
        # Structure: header rows, then "YESTERDAY ACTIVE" section, then "ALL SELLERS" section
        # Columns: Seller ID, Email, New/Returning, Questions Yesterday, Total Questions,
        #          Last Active, Days Silent, Engagement Trend, Classification,
        #          Channel Connection Status, Questions Used, Bill Plan,
        #          Questions Summary, Answers Summary, Action Detail

        sellers = []
        parsing = False
        for idx in range(len(raw_analytics)):
            row = raw_analytics.iloc[idx]
            vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]

            # Detect data rows (seller IDs are uppercase alphanumeric like AAFQY, GCK, GSK)
            seller_id = vals[0]
            if seller_id and re.match(r'^[A-Z0-9]{2,10}$', seller_id) and seller_id != "Seller ID":
                email = vals[1]
                new_ret = vals[2]
                try:
                    q_recent = int(float(vals[3])) if vals[3] else 0
                except:
                    q_recent = 0
                try:
                    q_total = int(float(vals[4])) if vals[4] else 0
                except:
                    q_total = 0
                last_active = vals[5]
                try:
                    days_silent = int(float(vals[6])) if vals[6] else 0
                except:
                    days_silent = 0
                trend = vals[7]
                classification = vals[8]
                q_summary = vals[12] if len(vals) > 12 else ""
                a_summary = vals[13] if len(vals) > 13 else ""
                action = vals[14] if len(vals) > 14 else ""

                sellers.append({
                    "seller_id": seller_id,
                    "email": email,
                    "type": new_ret,
                    "q_recent": q_recent,
                    "q_total": q_total,
                    "last_active": last_active,
                    "days_silent": days_silent,
                    "trend": trend,
                    "classification": classification,
                    "q_summary": q_summary,
                    "a_summary": a_summary,
                    "action": action,
                })

        if not sellers:
            st.warning("Could not parse seller data.")
        else:
            sellers_df = pd.DataFrame(sellers)

            # ── KPIs ──────────────────────────────────────────────────────────
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("Total Sellers", len(sellers_df))
            with c2:
                active = sellers_df[sellers_df["days_silent"] <= 7]
                st.metric("Active (7d)", len(active))
            with c3:
                power = sellers_df[sellers_df["classification"] == "Power User"]
                st.metric("Power Users", len(power))
            with c4:
                sales_ready = sellers_df[sellers_df["classification"] == "Sales-Ready"]
                st.metric("Sales-Ready", len(sales_ready))
            with c5:
                going_quiet = sellers_df[sellers_df["trend"] == "Going Quiet"]
                st.metric("Going Quiet", len(going_quiet), delta_color="inverse")

            # ── Filters ───────────────────────────────────────────────────────
            col_class, col_trend, col_search = st.columns(3)
            with col_class:
                classes = sorted(sellers_df["classification"].unique().tolist())
                sel_class = st.multiselect("Classification", classes, default=classes, key="acct_class")
            with col_trend:
                trends_list = sorted(sellers_df["trend"].unique().tolist())
                sel_trend = st.multiselect("Trend", trends_list, default=trends_list, key="acct_trend")
            with col_search:
                search = st.text_input("Search (ID or email)", "", key="acct_search")

            filtered = sellers_df[
                (sellers_df["classification"].isin(sel_class)) &
                (sellers_df["trend"].isin(sel_trend))
            ]
            if search:
                mask = (filtered["seller_id"].str.contains(search, case=False, na=False) |
                        filtered["email"].str.contains(search, case=False, na=False))
                filtered = filtered[mask]

            # ── Classification color coding ───────────────────────────────────
            def class_color(val):
                colors = {
                    "Sales-Ready": "background-color: #065F46; color: white",
                    "Power User": "background-color: #1E40AF; color: white",
                    "Explorer": "background-color: #92400E; color: white",
                    "Low Usage": "background-color: #78350F; color: white",
                    "Blocked": "background-color: #7F1D1D; color: white",
                }
                return colors.get(val, "")

            def trend_color(val):
                colors = {
                    "Highly Active": "color: #10B981",
                    "Active": "color: #06B6D4",
                    "Going Quiet": "color: #F59E0B",
                    "Churned": "color: #EF4444",
                }
                return colors.get(val, "")

            # ── Main Table ────────────────────────────────────────────────────
            display = filtered[["seller_id", "email", "type", "q_total", "q_recent",
                                "last_active", "days_silent", "trend", "classification"]].copy()
            display = display.sort_values("days_silent")

            st.dataframe(
                display.rename(columns={
                    "seller_id": "Seller", "email": "Email", "type": "New/Ret",
                    "q_total": "Total Q", "q_recent": "Recent Q",
                    "last_active": "Last Active", "days_silent": "Days Silent",
                    "trend": "Trend", "classification": "Class",
                }).style.applymap(class_color, subset=["Class"]).applymap(trend_color, subset=["Trend"]),
                use_container_width=True, height=500, hide_index=True,
            )

            # ── Classification & Trend Charts ────────────────────────────────
            ch1, ch2 = st.columns(2)
            with ch1:
                st.markdown("**By Classification**")
                class_counts = sellers_df["classification"].value_counts()
                fig_cl = px.pie(names=class_counts.index, values=class_counts.values,
                                color_discrete_sequence=["#065F46", "#1E40AF", "#92400E", "#78350F", "#7F1D1D"])
                fig_cl.update_layout(height=300, template="plotly_dark")
                st.plotly_chart(fig_cl, use_container_width=True)
            with ch2:
                st.markdown("**By Engagement Trend**")
                trend_counts = sellers_df["trend"].value_counts()
                fig_tr = px.pie(names=trend_counts.index, values=trend_counts.values,
                                color_discrete_sequence=["#10B981", "#06B6D4", "#F59E0B", "#EF4444"])
                fig_tr.update_layout(height=300, template="plotly_dark")
                st.plotly_chart(fig_tr, use_container_width=True)

            # ── Account Detail ────────────────────────────────────────────────
            st.markdown("### Account Detail")
            acct_names = filtered["seller_id"] + " — " + filtered["email"]
            selected = st.selectbox("Select account", acct_names.tolist(), key="acct_detail")

            if selected:
                sid = selected.split(" — ")[0]
                acct = sellers_df[sellers_df["seller_id"] == sid].iloc[0]

                col_info, col_action = st.columns([3, 2])
                with col_info:
                    st.markdown(f"**{acct['seller_id']}** — {acct['email']}")
                    st.markdown(f"Classification: **{acct['classification']}** | Trend: **{acct['trend']}** | "
                                f"Total Questions: **{acct['q_total']}** | Days Silent: **{acct['days_silent']}**")
                with col_action:
                    if acct["action"]:
                        st.info(acct["action"][:200])

                if acct["q_summary"]:
                    with st.expander("📋 Questions Summary"):
                        st.markdown(acct["q_summary"][:2000])
                if acct["a_summary"]:
                    with st.expander("📊 Answers Summary"):
                        st.markdown(acct["a_summary"][:2000])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: INTERESTING QUERIES
# ══════════════════════════════════════════════════════════════════════════════

with tab_queries:
    st.markdown("### Interesting Queries & Patterns")

    if raw_analytics.empty:
        st.warning("No query data. Download the 'Daily Analytics' tab from the Hoppr sheet.")
    elif 'sellers_df' not in dir() or sellers_df is None or sellers_df.empty:
        st.warning("Could not load seller data.")
    else:
        # ── Failed Intents — where Hoppr couldn't answer ─────────────────────
        st.markdown("#### ⚠️ Failed Intents — Where Hoppr Couldn't Answer")
        st.caption("These show gaps in data or capabilities that sellers are asking about")

        failed_sellers = []
        for _, s in sellers_df.iterrows():
            summary = s.get("a_summary", "") + " " + s.get("q_summary", "")
            if "failed" in summary.lower() or "⚠️" in summary:
                # Extract failed items
                failed_lines = [line.strip() for line in summary.split("•")
                                if "fail" in line.lower() or "⚠️" in line or "missing" in line.lower()]
                failed_sellers.append({
                    "Seller": s["seller_id"],
                    "Email": s["email"],
                    "Class": s["classification"],
                    "Total Q": s["q_total"],
                    "Failed Intents": " | ".join(failed_lines[:3])[:300] if failed_lines else "See detail",
                })

        if failed_sellers:
            st.metric("Sellers with Failed Queries", len(failed_sellers))
            st.dataframe(pd.DataFrame(failed_sellers), use_container_width=True, hide_index=True, height=400)
        else:
            st.success("No failed intents detected.")

        # ── Deep Analytics Users — advanced questions ─────────────────────────
        st.markdown("#### 🧠 Deep Analytics Users")
        st.caption("Sellers asking advanced analytical questions — strong product-market fit signals")

        deep_users = []
        for _, s in sellers_df.iterrows():
            summary = s.get("q_summary", "")
            if "deep analytics" in summary.lower() or "advanced analytical" in summary.lower():
                key_ask = ""
                for line in summary.split("•"):
                    if "key ask" in line.lower():
                        key_ask = line.strip()[:200]
                        break
                deep_users.append({
                    "Seller": s["seller_id"],
                    "Email": s["email"],
                    "Class": s["classification"],
                    "Total Q": s["q_total"],
                    "Key Ask": key_ask or summary[:200],
                })

        if deep_users:
            st.metric("Deep Analytics Users", len(deep_users))
            st.dataframe(pd.DataFrame(deep_users), use_container_width=True, hide_index=True, height=400)

        # ── Sales-Ready Sellers ───────────────────────────────────────────────
        st.markdown("#### 🎯 Sales-Ready — Action Required")
        st.caption("Sellers classified as sales-ready with recent activity")

        sales_ready = sellers_df[sellers_df["classification"] == "Sales-Ready"].copy()
        if not sales_ready.empty:
            sr_display = sales_ready[["seller_id", "email", "q_total", "days_silent", "trend"]].copy()
            sr_display = sr_display.sort_values("days_silent")
            st.dataframe(sr_display.rename(columns={
                "seller_id": "Seller", "email": "Email", "q_total": "Total Q",
                "days_silent": "Days Silent", "trend": "Trend",
            }), use_container_width=True, hide_index=True)

        # ── Power Users Going Quiet ───────────────────────────────────────────
        st.markdown("#### 🔕 Power Users Going Quiet")
        st.caption("High-usage sellers who are becoming inactive — potential churn risk")

        quiet_power = sellers_df[
            (sellers_df["classification"] == "Power User") &
            (sellers_df["trend"].isin(["Going Quiet", "Churned"]))
        ].copy()
        if not quiet_power.empty:
            qp_display = quiet_power[["seller_id", "email", "q_total", "days_silent", "trend", "last_active"]].copy()
            qp_display = qp_display.sort_values("days_silent")
            st.dataframe(qp_display.rename(columns={
                "seller_id": "Seller", "email": "Email", "q_total": "Total Q",
                "days_silent": "Days Silent", "trend": "Trend", "last_active": "Last Active",
            }), use_container_width=True, hide_index=True)
        else:
            st.success("No power users going quiet.")

        # ── Question Types Distribution ───────────────────────────────────────
        st.markdown("#### 📊 Common Question Types")
        st.caption("What sellers are asking about most")

        q_types = []
        for _, s in sellers_df.iterrows():
            summary = s.get("q_summary", "")
            if "question types:" in summary.lower():
                match = re.search(r'question types?:\s*(.+?)(?:\n|•|$)', summary, re.IGNORECASE)
                if match:
                    types = [t.strip().rstrip(".") for t in match.group(1).split(",")]
                    q_types.extend(types)

        if q_types:
            type_counts = pd.Series(q_types).value_counts().head(15)
            fig_qt = px.bar(
                x=type_counts.values, y=type_counts.index,
                orientation="h", color_discrete_sequence=["#4F46E5"],
                labels={"x": "Count", "y": "Question Type"},
            )
            fig_qt.update_layout(height=400, template="plotly_dark",
                                 margin=dict(l=20, r=20, t=20, b=20), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_qt, use_container_width=True)

        # ── Browse All Query Summaries ────────────────────────────────────────
        st.markdown("#### 🔍 Browse Query Summaries")
        browse_accts = sellers_df[sellers_df["q_summary"] != ""].sort_values("q_total", ascending=False)
        browse_names = (browse_accts["seller_id"] + " — " + browse_accts["email"] +
                        " (" + browse_accts["q_total"].astype(str) + " Q)").tolist()

        selected_q = st.selectbox("Select seller to view queries", browse_names[:50], key="browse_q")
        if selected_q:
            sid = selected_q.split(" — ")[0]
            acct = sellers_df[sellers_df["seller_id"] == sid].iloc[0]

            st.markdown(f"**{acct['seller_id']}** — {acct['email']} | "
                        f"Class: {acct['classification']} | Total: {acct['q_total']} questions")

            col_q, col_a = st.columns(2)
            with col_q:
                st.markdown("**Questions Asked:**")
                st.markdown(acct["q_summary"][:3000] if acct["q_summary"] else "No summary available")
            with col_a:
                st.markdown("**Answer Quality:**")
                st.markdown(acct["a_summary"][:3000] if acct["a_summary"] else "No summary available")
