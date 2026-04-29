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
    """Load Hoppr daily data — try Sheets API first, then CSV fallback."""
    try:
        from services.sheets_client import fetch_hoppr_analysis
        df = fetch_hoppr_analysis()
        if not df.empty:
            return df
    except Exception:
        pass
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Hoppr__Anaysis.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_funnel():
    """Load funnel data — try Sheets API first, then CSV fallback."""
    try:
        from services.sheets_client import fetch_sheet_tab
        import os
        sheet_id = os.getenv("HOPPR_SHEET_ID", "1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM")
        df = fetch_sheet_tab(sheet_id, "Final Funnel")
        if not df.empty:
            return df
    except Exception:
        pass
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Final Funnel.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, header=None)
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_daily_analytics():
    """Load daily analytics — try Sheets API first, then CSV fallback. 30-min cache for freshness."""
    try:
        from services.sheets_client import fetch_sheet_tab
        import os
        sheet_id = os.getenv("HOPPR_SHEET_ID", "1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM")
        df = fetch_sheet_tab(sheet_id, "Daily Analytics - Rohan", force_refresh=False)
        if not df.empty:
            return df
    except Exception:
        pass
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Daily Analytics - Rohan.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, header=None)
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_user_state():
    """Load User_State tab — live data updated by Rohan's daily script."""
    try:
        from services.sheets_client import fetch_sheet_tab
        import os
        sheet_id = os.getenv("HOPPR_SHEET_ID", "1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM")
        df = fetch_sheet_tab(sheet_id, "User_State", force_refresh=False)
        if not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_evaluation_sheet():
    """Load Evaluation_sheet tab — per-query log with all users per seller."""
    try:
        from services.sheets_client import fetch_sheet_tab
        import os
        sheet_id = os.getenv("HOPPR_SHEET_ID", "1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM")
        df = fetch_sheet_tab(sheet_id, "Evaluation_sheet", force_refresh=False)
        if not df.empty:
            return df
    except Exception:
        pass
    # CSV fallback
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Evaluation_sheet (1).csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()

raw_daily = load_hoppr_daily()
raw_funnel = load_funnel()
raw_analytics = load_daily_analytics()
raw_user_state = load_user_state()
raw_eval = load_evaluation_sheet()

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Process daily data
daily = process_hoppr_daily(raw_daily) if not raw_daily.empty else pd.DataFrame()
country = process_hoppr_country(raw_daily) if not raw_daily.empty else pd.DataFrame()

# ══════════════════════════════════════════════════════════════════════════════

tab_funnel, tab_accounts, tab_queries, tab_deep_dive = st.tabs([
    "🔄 Funnel",
    "👥 Key Accounts",
    "💬 Interesting Queries",
    "🔍 Account Deep Dive",
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

        # Period selector — filters actual data passed to chart
        period = st.radio(
            "Period",
            ["1W", "1M", "3M", "All"],
            index=1,
            horizontal=True,
            key="hoppr_period",
        )
        today_ts = daily["date"].max()
        data_start = daily["date"].min()
        cutoffs = {"1W": today_ts - pd.Timedelta(days=7),
                   "1M": today_ts - pd.Timedelta(days=30),
                   "3M": today_ts - pd.Timedelta(days=90)}
        if period in cutoffs:
            cutoff = max(cutoffs[period], data_start)  # don't go before data start
            daily_f = daily[daily["date"] >= cutoff]
            country_f = country[country["date"] >= cutoff] if not country.empty and "date" in country.columns else country
        else:
            daily_f = daily
            country_f = country

        # Show what the filter is actually covering
        f_start = daily_f["date"].min().strftime("%-d %b %Y") if not daily_f.empty else "—"
        f_end   = daily_f["date"].max().strftime("%-d %b %Y") if not daily_f.empty else "—"
        data_days = (daily["date"].max() - daily["date"].min()).days + 1
        if period in cutoffs and cutoffs[period] < data_start:
            st.caption(f"📅 {f_start} → {f_end} · {len(daily_f)} days  "
                       f"_(data only goes back {data_days} days — {period} view shows the same as All)_")
        else:
            st.caption(f"📅 {f_start} → {f_end} · {len(daily_f)} days")

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

        # Country breakdown — filtered by selected date range
        if not country_f.empty:
            st.markdown("### By Country")
            ca = country_f.groupby("country").agg({"total_queries": "sum", "unique_sellers": "sum"}).reset_index()
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

    # ── Parse User_State (live data) ─────────────────────────────────────────
    sellers = []
    if not raw_user_state.empty:
        from datetime import datetime as _dt
        _today = _dt.now().date()

        for idx in range(len(raw_user_state)):
            row = raw_user_state.iloc[idx]
            vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]

            seller_id = vals[0]
            if not seller_id or seller_id in ("user_key", "") or not re.match(r'^[A-Z0-9]{2,10}$', seller_id):
                continue

            email = vals[2] if len(vals) > 2 else ""
            last_seen = vals[3] if len(vals) > 3 else ""
            try:
                q_total = int(float(vals[4])) if len(vals) > 4 and vals[4] else 0
            except:
                q_total = 0
            try:
                q_7d = int(float(vals[5])) if len(vals) > 5 and vals[5] else 0
            except:
                q_7d = 0

            # Calculate days silent from last_seen
            days_silent = 999
            if last_seen:
                try:
                    ls_date = _dt.strptime(last_seen, "%Y-%m-%d").date()
                    days_silent = (_today - ls_date).days
                except:
                    pass

            summary = vals[6] if len(vals) > 6 else ""
            bucket = vals[7] if len(vals) > 7 else ""
            action = vals[8] if len(vals) > 8 else ""
            reason = vals[9] if len(vals) > 9 else ""

            # Map bucket to classification/trend
            bucket_lower = bucket.lower()
            if "sales" in bucket_lower or "ready" in bucket_lower:
                classification = "Sales-Ready"
            elif "power" in bucket_lower:
                classification = "Power User"
            elif "explor" in bucket_lower:
                classification = "Explorer"
            elif "block" in bucket_lower:
                classification = "Blocked"
            else:
                classification = "Low Usage"

            if days_silent <= 1:
                trend = "Highly Active"
            elif days_silent <= 7:
                trend = "Active"
            elif days_silent <= 30:
                trend = "Going Quiet"
            else:
                trend = "Churned"

            sellers.append({
                "seller_id": seller_id,
                "email": email,
                "type": "",
                "q_recent": q_7d,
                "q_total": q_total,
                "last_active": last_seen,
                "days_silent": days_silent,
                "trend": trend,
                "classification": classification,
                "q_summary": summary,
                "a_summary": reason,
                "action": action,
            })

    # ── Build per-seller user map from Evaluation_sheet ────────────────────
    seller_users_map = {}  # seller_id -> list of {email, dates, query_count}
    if not raw_eval.empty:
        # Normalise column names
        eval_df = raw_eval.copy()
        eval_cols = [str(c).strip() for c in eval_df.columns]
        # Find Seller ID and Email ID columns
        sid_col = next((c for c in eval_cols if "seller" in c.lower() and "id" in c.lower()), None)
        email_col = next((c for c in eval_cols if "email" in c.lower()), None)
        date_col = next((c for c in eval_cols if c.lower() == "date"), None)
        if sid_col and email_col:
            for _, row in eval_df.iterrows():
                sid = str(row.get(sid_col, "")).strip()
                em = str(row.get(email_col, "")).strip()
                dt = str(row.get(date_col, "")).strip() if date_col else ""
                if not sid or not em or sid == "nan" or em == "nan":
                    continue
                if sid not in seller_users_map:
                    seller_users_map[sid] = {}
                if em not in seller_users_map[sid]:
                    seller_users_map[sid][em] = {"dates": [], "count": 0}
                seller_users_map[sid][em]["count"] += 1
                if dt and dt != "nan":
                    seller_users_map[sid][em]["dates"].append(dt)

    # Enrich sellers with user count and all emails
    for s in sellers:
        sid = s["seller_id"]
        if sid in seller_users_map:
            user_info = seller_users_map[sid]
            s["user_count"] = len(user_info)
            s["all_emails"] = list(user_info.keys())
            s["user_details"] = {
                em: {"count": info["count"], "last_date": max(info["dates"]) if info["dates"] else ""}
                for em, info in user_info.items()
            }
        else:
            s["user_count"] = 1
            s["all_emails"] = [s["email"]]
            s["user_details"] = {}

    # ── Staleness indicator ──────────────────────────────────────────────────
    _rohan_date = ""
    if not raw_analytics.empty:
        header_str = str(raw_analytics.iloc[0, 0]) if len(raw_analytics) > 0 else ""
        date_match = re.search(r'Data as of (.+?)$', header_str)
        if date_match:
            _rohan_date = date_match.group(1).strip()

    if sellers:
        # Source label
        latest_seen = max(s["last_active"] for s in sellers if s["last_active"])
        source_label = f"Source: **User_State** (latest: {latest_seen})"
        if _rohan_date:
            source_label += f"  |  Rohan Daily Sheet: **{_rohan_date}**"
            try:
                from datetime import datetime as _dt2
                rd = _dt2.strptime(_rohan_date.replace(",", ""), "%b %d %Y").date()
                stale_days = (_dt.now().date() - rd).days
                if stale_days > 2:
                    source_label += f" :red[({stale_days}d stale)]"
            except:
                pass
        st.caption(source_label)
    elif not raw_analytics.empty:
        # Fallback to Rohan sheet
        st.caption(f"Source: **Rohan Daily Sheet** ({_rohan_date}) — :red[User_State unavailable]")

    if not sellers:
        st.warning("No account data available.")
    else:
        sellers_df = pd.DataFrame(sellers)

        # ── KPIs ──────────────────────────────────────────────────────────
        total_users = sellers_df["user_count"].sum() if "user_count" in sellers_df.columns else len(sellers_df)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("Total Sellers", len(sellers_df))
        with c2:
            st.metric("Total Users", int(total_users))
        with c3:
            active = sellers_df[sellers_df["days_silent"] <= 7]
            st.metric("Active (7d)", len(active))
        with c4:
            power = sellers_df[sellers_df["classification"] == "Power User"]
            st.metric("Power Users", len(power))
        with c5:
            sales_ready = sellers_df[sellers_df["classification"] == "Sales-Ready"]
            st.metric("Sales-Ready", len(sales_ready))
        with c6:
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
        display = filtered[["seller_id", "email", "user_count", "q_total", "q_recent",
                            "last_active", "days_silent", "trend", "classification"]].copy()
        display = display.sort_values("days_silent")

        st.dataframe(
            display.rename(columns={
                "seller_id": "Seller", "email": "Email", "user_count": "Users",
                "q_total": "Total Q", "q_recent": "Q (7d)",
                "last_active": "Last Active", "days_silent": "Days Silent",
                "trend": "Trend", "classification": "Class",
            }).style.map(class_color, subset=["Class"]).map(trend_color, subset=["Trend"]),
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
                user_count = acct.get("user_count", 1)
                st.markdown(f"Classification: **{acct['classification']}** | Trend: **{acct['trend']}** | "
                            f"Total Questions: **{acct['q_total']}** | Days Silent: **{acct['days_silent']}** | "
                            f"Users: **{user_count}**")
            with col_action:
                if acct["action"]:
                    st.info(acct["action"][:200])

            # Show all users for this seller (from Evaluation_sheet)
            user_details = acct.get("user_details", {})
            all_emails = acct.get("all_emails", [acct["email"]])
            if len(all_emails) > 1:
                with st.expander(f"👥 All Users ({len(all_emails)})"):
                    user_rows = []
                    for em in all_emails:
                        detail = user_details.get(em, {})
                        user_rows.append({
                            "Email": em,
                            "Queries": detail.get("count", 0),
                            "Last Active": detail.get("last_date", ""),
                        })
                    user_rows.sort(key=lambda x: x["Last Active"], reverse=True)
                    st.dataframe(pd.DataFrame(user_rows), use_container_width=True, hide_index=True)

            if acct["q_summary"]:
                with st.expander("📋 Running Summary"):
                    st.markdown(acct["q_summary"][:2000])
            if acct["a_summary"]:
                with st.expander("📊 Reason / Detail"):
                    st.markdown(acct["a_summary"][:2000])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: INTERESTING QUERIES
# ══════════════════════════════════════════════════════════════════════════════

with tab_queries:
    st.markdown("### Interesting Queries & Patterns")

    # Interesting Queries uses Rohan's detailed sheet (has per-question Q&A breakdowns)
    # Build rohan_sellers_df from raw_analytics for this tab
    rohan_sellers = []
    if not raw_analytics.empty:
        for idx in range(len(raw_analytics)):
            row = raw_analytics.iloc[idx]
            vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
            seller_id = vals[0]
            if seller_id and re.match(r'^[A-Z0-9]{2,10}$', seller_id) and seller_id != "Seller ID":
                try:
                    q_total = int(float(vals[4])) if vals[4] else 0
                except:
                    q_total = 0
                rohan_sellers.append({
                    "seller_id": seller_id, "email": vals[1],
                    "classification": vals[8], "trend": vals[7],
                    "q_total": q_total, "q_recent": 0,
                    "q_summary": vals[12] if len(vals) > 12 else "",
                    "a_summary": vals[13] if len(vals) > 13 else "",
                    "action": vals[14] if len(vals) > 14 else "",
                    "last_active": vals[5], "days_silent": 0,
                })

    if not rohan_sellers:
        st.warning("No query data. Rohan Daily Sheet is needed for detailed Q&A analysis.")
    else:
        rohan_sellers_df = pd.DataFrame(rohan_sellers)

        # Staleness label
        _rohan_date_q = ""
        header_str_q = str(raw_analytics.iloc[0, 0]) if len(raw_analytics) > 0 else ""
        date_match_q = re.search(r'Data as of (.+?)$', header_str_q)
        if date_match_q:
            _rohan_date_q = date_match_q.group(1).strip()
        if _rohan_date_q:
            stale_label = f"Source: **Rohan Daily Sheet** ({_rohan_date_q})"
            try:
                from datetime import datetime as _dt3
                rd_q = _dt3.strptime(_rohan_date_q.replace(",", ""), "%b %d %Y").date()
                stale_days_q = (_dt3.now().date() - rd_q).days
                if stale_days_q > 2:
                    stale_label += f" :red[({stale_days_q}d stale)]"
            except:
                pass
            st.caption(stale_label)

        # Alias for downstream code
        sellers_df = rohan_sellers_df

        # ── 1. Common Question Types (TOP) ────────────────────────────────────
        st.markdown("#### 📊 Common Question Types")
        st.caption("What sellers are asking about most — sets context for everything below")

        q_types = []
        for _, s in sellers_df.iterrows():
            summary = s.get("q_summary", "")
            if "question types:" in summary.lower():
                match = re.search(r'question types?:\s*(.+?)(?:\n|•|$)', summary, re.IGNORECASE)
                if match:
                    types = [t.strip().rstrip(".") for t in match.group(1).split(",")]
                    q_types.extend([t for t in types if t])

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

        # ── 2. Failed Intents — parsed properly ──────────────────────────────
        st.markdown("---")
        st.markdown("#### ⚠️ Failed Intents — Where Hoppr Couldn't Answer")
        st.caption("Gaps in data or capabilities — refreshed every 30 min from the sheet")

        failed_items = []
        for _, s in sellers_df.iterrows():
            q_summary = s.get("q_summary", "")
            a_summary = s.get("a_summary", "")
            # Parse each bullet from q_summary for failed items
            for bullet in q_summary.split("•"):
                bullet = bullet.strip()
                if not bullet:
                    continue
                if "failed" in bullet.lower() or "⚠️" in bullet:
                    # Extract the question and failure reason
                    # Format: "Q1: [question] — Failed: [reason]" or "Q1: [question] — [Answer: Answered]"
                    q_match = re.match(r'Q\d+:\s*(.+?)(?:\s*—\s*(?:Failed|Answer))', bullet, re.IGNORECASE)
                    question = q_match.group(1).strip().strip("[]") if q_match else ""
                    reason_match = re.search(r'Failed:?\s*(.+?)(?:$)', bullet, re.IGNORECASE)
                    reason = reason_match.group(1).strip().strip(".") if reason_match else ""
                    # Also check a_summary for more detail on failure
                    if not reason:
                        reason_match2 = re.search(r'⚠️\s*(.+?)(?:$)', bullet, re.IGNORECASE)
                        reason = reason_match2.group(1).strip() if reason_match2 else "See detail"
                    failed_items.append({
                        "Seller": s["seller_id"],
                        "Email": s["email"],
                        "Question": question[:200] if question else bullet[:200],
                        "Failure Reason": reason[:200] if reason else "See detail",
                        "Class": s["classification"],
                    })

        if failed_items:
            fail_df = pd.DataFrame(failed_items)

            # Summary metrics
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                st.metric("Failed Queries", len(fail_df))
            with fc2:
                st.metric("Sellers Affected", fail_df["Seller"].nunique())
            with fc3:
                # Most common failure pattern
                top_reason = fail_df["Failure Reason"].value_counts().index[0][:40] if len(fail_df) > 0 else "—"
                st.metric("Top Failure", top_reason)

            st.dataframe(fail_df, use_container_width=True, hide_index=True, height=400)
        else:
            st.success("No failed intents detected.")

        # ── 3. Deep Analytics Users — clearer Key Ask ─────────────────────────
        st.markdown("---")
        st.markdown("#### 🧠 Deep Analytics Users")
        st.caption("Sellers asking advanced analytical questions — strong product-market fit signals")

        deep_users = []
        for _, s in sellers_df.iterrows():
            summary = s.get("q_summary", "")
            if "deep analytics" in summary.lower() or "advanced analytical" in summary.lower():
                # Try to extract "Key ask of customer:" line
                key_ask = ""
                key_match = re.search(r'key ask(?:\s+of\s+customer)?:\s*(.+?)(?:\n|•|$)', summary, re.IGNORECASE)
                if key_match:
                    key_ask = key_match.group(1).strip().rstrip(".")

                # Extract question types if available
                q_types_str = ""
                qt_match = re.search(r'question types?:\s*(.+?)(?:\n|•|$)', summary, re.IGNORECASE)
                if qt_match:
                    q_types_str = qt_match.group(1).strip().rstrip(".")

                # If no key ask found, use the first Q1 question
                if not key_ask:
                    q1_match = re.search(r'Q1:\s*(.+?)(?:\s*—\s*(?:\[?(?:Answer|Failed)))', summary, re.IGNORECASE)
                    if q1_match:
                        key_ask = q1_match.group(1).strip().strip("[]")
                    else:
                        # Last resort: first meaningful line
                        key_ask = summary.split("•")[1].strip()[:150] if "•" in summary and len(summary.split("•")) > 1 else summary[:150]

                deep_users.append({
                    "Seller": s["seller_id"],
                    "Email": s["email"],
                    "Class": s["classification"],
                    "Total Q": s["q_total"],
                    "Key Ask": key_ask[:200],
                    "Question Types": q_types_str[:200] if q_types_str else "—",
                })

        if deep_users:
            st.metric("Deep Analytics Users", len(deep_users))
            st.dataframe(pd.DataFrame(deep_users), use_container_width=True, hide_index=True, height=400)

        # ── 4. Sales-Ready Sellers ────────────────────────────────────────────
        st.markdown("---")
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

        # ── 5. Power Users Going Quiet ────────────────────────────────────────
        st.markdown("---")
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

        # ── 6. Browse Query Summaries — multiple sellers ──────────────────────
        st.markdown("---")
        st.markdown("#### 🔍 Browse Query Summaries")
        st.caption("Top sellers by query volume — expand any card to see full Q&A detail")

        browse_accts = sellers_df[sellers_df["q_summary"] != ""].sort_values("q_total", ascending=False)

        # Search filter
        browse_search = st.text_input("Filter by seller ID or email", "", key="browse_search")
        if browse_search:
            browse_accts = browse_accts[
                browse_accts["seller_id"].str.contains(browse_search, case=False, na=False) |
                browse_accts["email"].str.contains(browse_search, case=False, na=False)
            ]

        # Show top 15 as expandable cards
        show_count = min(15, len(browse_accts))

        # Extract report date from header if available
        _report_date = ""
        if not raw_analytics.empty:
            header_str = str(raw_analytics.columns[0])
            date_match = re.search(r'Data as of (.+?)$', header_str)
            if date_match:
                _report_date = date_match.group(1).strip()

        if _report_date:
            st.caption(f"Showing top {show_count} of {len(browse_accts)} sellers | Report date: **{_report_date}** | Each seller shows all their queries (not just one day)")
        else:
            st.caption(f"Showing top {show_count} of {len(browse_accts)} sellers with query data")

        for _, acct in browse_accts.head(show_count).iterrows():
            # Build a one-line preview from q_summary
            preview = ""
            if acct["q_summary"]:
                first_q = re.search(r'Q1:\s*(.+?)(?:\s*—|$)', acct["q_summary"])
                if first_q:
                    preview = first_q.group(1).strip()[:80]
                else:
                    preview = acct["q_summary"][:80].replace("\n", " ")

            # Activity info
            last_active = acct.get("last_active", "")
            days_silent = acct.get("days_silent", "")
            recent_q = acct.get("q_recent", "")
            activity_tag = ""
            if last_active:
                activity_tag = f"Last active: {last_active}"
                if recent_q:
                    activity_tag += f" | {recent_q} recent"

            label = (f"**{acct['seller_id']}** — {acct['email']} | "
                     f"{acct['classification']} | {acct['q_total']}Q total | "
                     f"{activity_tag}")

            with st.expander(label):
                # Quick metadata row
                mc1, mc2, mc3, mc4 = st.columns(4)
                with mc1:
                    st.markdown(f"**Total Questions:** {acct['q_total']}")
                with mc2:
                    st.markdown(f"**Recent Questions:** {recent_q if recent_q else '—'}")
                with mc3:
                    st.markdown(f"**Last Active:** {last_active if last_active else '—'}")
                with mc4:
                    st.markdown(f"**Trend:** {acct.get('trend', '—')}")

                col_q, col_a = st.columns(2)
                with col_q:
                    st.markdown("**Questions Asked:**")
                    st.markdown(acct["q_summary"][:3000] if acct["q_summary"] else "No summary available")
                with col_a:
                    st.markdown("**Answer Quality:**")
                    st.markdown(acct["a_summary"][:3000] if acct["a_summary"] else "No summary available")
                if acct.get("action"):
                    st.info(f"**Recommended Action:** {acct['action'][:300]}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: ACCOUNT DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════════

with tab_deep_dive:
    st.markdown("### 🔍 Account Deep Dive")
    st.caption("One-page summary of any seller — users, query timeline, gaps, and recommendations")

    # Build seller list from evaluation sheet
    if raw_eval.empty:
        st.warning("No Evaluation_sheet data available.")
    else:
        eval_df = raw_eval.copy()
        eval_cols = [str(c).strip() for c in eval_df.columns]
        sid_col_dd = next((c for c in eval_cols if "seller" in c.lower() and "id" in c.lower()), None)
        email_col_dd = next((c for c in eval_cols if "email" in c.lower()), None)
        date_col_dd = next((c for c in eval_cols if c.lower() == "date"), None)
        q_col_dd = next((c for c in eval_cols if "question" in c.lower()), None)
        a_col_dd = next((c for c in eval_cols if "answer" in c.lower()), None)

        if not sid_col_dd:
            st.error("Cannot find Seller ID column in Evaluation_sheet")
        else:
            # Build list of sellers with query counts
            seller_q_counts = eval_df[sid_col_dd].value_counts().to_dict()
            seller_ids = sorted(seller_q_counts.keys(), key=lambda x: -seller_q_counts[x])

            # Selectbox with query count
            options = [f"{sid} ({seller_q_counts[sid]}Q)" for sid in seller_ids]
            selected_dd = st.selectbox("Select seller", options, key="dd_seller")
            sel_sid = selected_dd.split(" (")[0] if selected_dd else None

            if sel_sid:
                acct_rows = eval_df[eval_df[sid_col_dd] == sel_sid].copy()

                # ── At a Glance ──────────────────────────────────────────────
                emails = acct_rows[email_col_dd].unique().tolist() if email_col_dd else []
                dates = sorted(acct_rows[date_col_dd].dropna().unique().tolist()) if date_col_dd else []
                first_date = dates[0] if dates else "—"
                last_date = dates[-1] if dates else "—"
                total_q = len(acct_rows)

                # Get User_State info if available
                us_summary = ""
                us_answer = ""
                us_action = ""
                us_class = ""
                us_bucket = ""
                if not raw_user_state.empty:
                    for idx in range(len(raw_user_state)):
                        row = raw_user_state.iloc[idx]
                        vals = [str(v).strip() if str(v) != "nan" else "" for v in row.values]
                        if vals[0] == sel_sid:
                            us_summary = vals[6] if len(vals) > 6 else ""
                            us_bucket = vals[7] if len(vals) > 7 else ""
                            us_action = vals[8] if len(vals) > 8 else ""
                            us_answer = vals[9] if len(vals) > 9 else ""
                            break

                # Get Rohan sheet info
                rohan_summary = ""
                rohan_answer = ""
                rohan_class = ""
                rohan_trend = ""
                if not raw_analytics.empty:
                    for idx in range(len(raw_analytics)):
                        row = raw_analytics.iloc[idx]
                        vals = [str(v).strip() if str(v) != "nan" else "" for v in row.values]
                        if vals[0] == sel_sid:
                            rohan_class = vals[8] if len(vals) > 8 else ""
                            rohan_trend = vals[7] if len(vals) > 7 else ""
                            rohan_summary = vals[12] if len(vals) > 12 else ""
                            rohan_answer = vals[13] if len(vals) > 13 else ""
                            break

                classification = rohan_class or us_bucket or "—"
                trend = rohan_trend or "—"

                # ── KPI row ──────────────────────────────────────────────────
                k1, k2, k3, k4, k5 = st.columns(5)
                with k1:
                    st.metric("Total Queries", total_q)
                with k2:
                    st.metric("Users", len(emails))
                with k3:
                    st.metric("First Active", first_date)
                with k4:
                    st.metric("Last Active", last_date)
                with k5:
                    st.metric("Classification", classification)

                st.markdown("---")

                # ── Users Table ──────────────────────────────────────────────
                st.markdown("#### 👥 Users")

                # Classify questions into types
                def _classify_question(q_text):
                    """Classify a question into broad types based on keywords."""
                    q = q_text.lower()
                    tags = []
                    if any(w in q for w in ["revenue", "gmv", "sales", "selling", "growth"]):
                        tags.append("Revenue/Sales")
                    if any(w in q for w in ["sku", "product", "listing"]):
                        tags.append("Product/SKU")
                    if any(w in q for w in ["traffic", "visitor", "visit"]):
                        tags.append("Traffic")
                    if any(w in q for w in ["ad ", "ads ", "roas", "campaign", "paid", "advertisement"]):
                        tags.append("Ads/ROAS")
                    if any(w in q for w in ["affiliate", "creator", "commission", "partner"]):
                        tags.append("Affiliates")
                    if any(w in q for w in ["kpi", "compare", "comparison", "vs ", "versus"]):
                        tags.append("KPI Comparison")
                    if any(w in q for w in ["decline", "drop", "reason", "root cause", "why"]):
                        tags.append("Root Cause")
                    if any(w in q for w in ["optimis", "recommend", "should i", "how to"]):
                        tags.append("Optimisation")
                    if any(w in q for w in ["year on year", "yoy", "last year"]):
                        tags.append("YoY Analysis")
                    if any(w in q for w in ["country", "market", "malaysia", "philippines", "thailand", "indonesia"]):
                        tags.append("Market/Geo")
                    if not tags:
                        tags.append("General")
                    return tags

                user_rows = []
                for em in emails:
                    em_rows = acct_rows[acct_rows[email_col_dd] == em]
                    em_dates = sorted(em_rows[date_col_dd].dropna().unique().tolist()) if date_col_dd else []
                    # Classify all questions for this user
                    all_tags = []
                    questions_preview = []
                    for _, qr in em_rows.iterrows():
                        q_text = str(qr.get(q_col_dd, "")) if q_col_dd else ""
                        tags = _classify_question(q_text)
                        all_tags.extend(tags)
                        questions_preview.append(q_text[:80])
                    # Deduplicate and count tag frequency
                    tag_counts = pd.Series(all_tags).value_counts()
                    top_types = ", ".join(tag_counts.index.tolist()[:4])

                    user_rows.append({
                        "Email": em,
                        "Queries": len(em_rows),
                        "Question Types": top_types,
                        "First Active": em_dates[0] if em_dates else "—",
                        "Last Active": em_dates[-1] if em_dates else "—",
                        "_questions": questions_preview,
                    })
                user_rows.sort(key=lambda x: -x["Queries"])

                # Show table
                st.dataframe(
                    pd.DataFrame(user_rows)[["Email", "Queries", "Question Types", "First Active", "Last Active"]],
                    use_container_width=True, hide_index=True,
                )

                # Expandable per-user question list
                for ur in user_rows:
                    em_short = ur["Email"].split("@")[0] if "@" in ur["Email"] else ur["Email"]
                    with st.expander(f"📋 {em_short} — {ur['Queries']} questions"):
                        for i, q in enumerate(ur["_questions"], 1):
                            st.markdown(f"{i}. {q}")

                # ── Query Timeline ───────────────────────────────────────────
                st.markdown("#### 📋 Query Timeline")

                for _, qrow in acct_rows.iterrows():
                    dt = str(qrow.get(date_col_dd, "")) if date_col_dd else ""
                    em = str(qrow.get(email_col_dd, "")) if email_col_dd else ""
                    question = str(qrow.get(q_col_dd, ""))[:200] if q_col_dd else ""
                    answer = str(qrow.get(a_col_dd, "")) if a_col_dd else ""

                    # Quality indicator
                    has_data = any(c in answer for c in ["📊", "|", "%", "table"])
                    failed = any(w in answer.lower() for w in ["unable", "don't have", "not available", "cannot provide", "no data"])
                    if failed:
                        status = "⚠️"
                    elif has_data:
                        status = "✅"
                    else:
                        status = "➡️"

                    em_short = em.split("@")[0] if "@" in em else em
                    with st.expander(f"{status} {dt} — **{em_short}** — {question}"):
                        st.markdown(f"**Q:** {question}")
                        st.markdown("**A (preview):**")
                        st.markdown(answer[:800] if answer else "No answer recorded")

                # ── AI Summary ───────────────────────────────────────────────
                summary_text = rohan_summary or us_summary
                answer_text = rohan_answer or us_answer

                if summary_text or answer_text:
                    st.markdown("---")
                    st.markdown("#### 🧠 AI Analysis")
                    col_s, col_a = st.columns(2)
                    with col_s:
                        st.markdown("**What they're asking about:**")
                        st.markdown(summary_text[:2000] if summary_text else "—")
                    with col_a:
                        st.markdown("**Answer quality assessment:**")
                        st.markdown(answer_text[:2000] if answer_text else "—")

                if us_action:
                    st.info(f"**Recommended Action:** {us_action[:500]}")
