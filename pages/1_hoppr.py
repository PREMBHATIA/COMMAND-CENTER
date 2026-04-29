"""Hoppr Usage Dashboard — Home · Accounts · Ask Hoppr"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import re
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
from services.data_processor import (
    process_hoppr_daily, process_hoppr_daily_from_eval,
    process_hoppr_country, compute_hoppr_wow,
)

st.set_page_config(page_title="Hoppr | Graas", page_icon="📊", layout="wide")
st.markdown("## 📊 Hoppr")

# ── Data Loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_hoppr_daily():
    try:
        from services.sheets_client import fetch_hoppr_analysis
        df = fetch_hoppr_analysis()
        if not df.empty:
            return df
    except Exception:
        pass
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Hoppr__Anaysis.csv"
    return pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()

@st.cache_data(ttl=1800)
def load_evaluation_sheet():
    try:
        from services.sheets_client import fetch_sheet_tab
        sheet_id = os.getenv("HOPPR_SHEET_ID", "1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM")
        df = fetch_sheet_tab(sheet_id, "Evaluation_sheet", force_refresh=False)
        if not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_user_state():
    try:
        from services.sheets_client import fetch_sheet_tab
        sheet_id = os.getenv("HOPPR_SHEET_ID", "1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM")
        df = fetch_sheet_tab(sheet_id, "User_State", force_refresh=False)
        if not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_daily_analytics():
    try:
        from services.sheets_client import fetch_sheet_tab
        sheet_id = os.getenv("HOPPR_SHEET_ID", "1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM")
        df = fetch_sheet_tab(sheet_id, "Daily Analytics - Rohan", force_refresh=False)
        if not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_funnel():
    try:
        from services.sheets_client import fetch_sheet_tab
        sheet_id = os.getenv("HOPPR_SHEET_ID", "1IR6KuRhPMRj_JsF261ZEUjLlHXu6UZ33diZQRw2MqJM")
        df = fetch_sheet_tab(sheet_id, "Final Funnel")
        if not df.empty:
            return df
    except Exception:
        pass
    csv_path = Path.home() / "Downloads" / "hoppr Dashboard - Final Funnel.csv"
    return pd.read_csv(csv_path, header=None) if csv_path.exists() else pd.DataFrame()

# ── Fetch ─────────────────────────────────────────────────────────────────────

raw_daily      = load_hoppr_daily()
raw_eval       = load_evaluation_sheet()
raw_user_state = load_user_state()
raw_analytics  = load_daily_analytics()
raw_funnel     = load_funnel()

col_r, _ = st.columns([1, 9])
with col_r:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Build daily metrics (prefer Evaluation_sheet — full 6-month history) ─────

daily_from_analysis = process_hoppr_daily(raw_daily) if not raw_daily.empty else pd.DataFrame()
daily_from_eval     = process_hoppr_daily_from_eval(raw_eval) if not raw_eval.empty else pd.DataFrame()

if not daily_from_eval.empty and (
    daily_from_analysis.empty or len(daily_from_eval) > len(daily_from_analysis) + 7
):
    daily = daily_from_eval
else:
    daily = daily_from_analysis

country = process_hoppr_country(raw_daily) if not raw_daily.empty else pd.DataFrame()

# ── Question classification ───────────────────────────────────────────────────

ACCURACY_KEYWORDS = [
    "wrong", "incorrect", "inaccurate", "not matching", "doesn't match",
    "mismatch", "missing data", "no data", "data not", "data accuracy",
    "data quality", "data issue", "different from", "discrepancy",
    "not available", "not showing", "showing wrong", "can't find",
    "cannot find", "not found",
]

QUESTION_BUCKETS = {
    "Revenue / Sales":  ["revenue", "gmv", "sales", "selling", "growth", "income", "orders"],
    "Ads / ROAS":       ["roas", "campaign", "paid", "advertisement", "spend", " ad ", " ads "],
    "Traffic":          ["traffic", "visitor", "visit", "session", "pageview", "click"],
    "Product / SKU":    ["sku", "product", "listing", "catalogue", "catalog", "item"],
    "Affiliates":       ["affiliate", "creator", "commission", "partner", "influencer"],
    "Root Cause":       ["decline", "drop", "reason", "root cause", "why", "fell", "decreased"],
    "Comparison / KPI": ["kpi", "compare", "comparison", " vs ", "versus", "benchmark"],
    "Optimisation":     ["optimis", "optimiz", "recommend", "should i", "how to", "improve"],
    "YoY / Trends":     ["year on year", "yoy", "last year", "month on month", "trend"],
    "Market / Geo":     ["country", "market", "malaysia", "philippines", "thailand", "indonesia", "india"],
    "Data Accuracy":    ACCURACY_KEYWORDS,
}

def classify_question(q: str) -> list:
    ql = q.lower()
    tags = [b for b, kws in QUESTION_BUCKETS.items() if any(kw in ql for kw in kws)]
    return tags if tags else ["General"]

def is_accuracy(q: str) -> bool:
    ql = q.lower()
    return any(kw in ql for kw in ACCURACY_KEYWORDS)

# ── Pre-process eval sheet ────────────────────────────────────────────────────

eval_processed = pd.DataFrame()
sid_col_e = email_col_e = date_col_e = q_col_e = a_col_e = None

if not raw_eval.empty:
    edf = raw_eval.copy()
    ecols = [str(c).strip() for c in edf.columns]
    edf.columns = ecols
    sid_col_e   = next((c for c in ecols if "seller" in c.lower() and "id" in c.lower()), None)
    email_col_e = next((c for c in ecols if "email" in c.lower()), None)
    date_col_e  = next((c for c in ecols if c.lower() == "date"), None)
    q_col_e     = next((c for c in ecols if "question" in c.lower()), None)
    a_col_e     = next((c for c in ecols if "answer" in c.lower()), None)

    if sid_col_e and date_col_e and q_col_e:
        edf["_date"]     = pd.to_datetime(edf[date_col_e], errors="coerce")
        edf["_week"]     = edf["_date"].dt.to_period("W").dt.start_time
        edf["_seller"]   = edf[sid_col_e].astype(str).str.strip()
        edf["_email"]    = edf[email_col_e].astype(str).str.strip() if email_col_e else ""
        edf["_question"] = edf[q_col_e].astype(str)
        edf["_answer"]   = edf[a_col_e].astype(str) if a_col_e else ""
        edf = edf.dropna(subset=["_date"])
        edf["_is_accuracy"] = edf["_question"].apply(is_accuracy)
        edf["_buckets"]     = edf["_question"].apply(classify_question)
        eval_processed = edf

# ── Parse sellers from User_State ─────────────────────────────────────────────

sellers = []
seller_users_map = {}

if not raw_user_state.empty:
    from datetime import datetime as _dt
    _today = _dt.now().date()

    for idx in range(len(raw_user_state)):
        row  = raw_user_state.iloc[idx]
        vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
        sid  = vals[0]
        if not sid or sid in ("user_key", "") or not re.match(r'^[A-Z0-9]{2,10}$', sid):
            continue
        email     = vals[2] if len(vals) > 2 else ""
        last_seen = vals[3] if len(vals) > 3 else ""
        try:    q_total = int(float(vals[4])) if len(vals) > 4 and vals[4] else 0
        except: q_total = 0
        try:    q_7d = int(float(vals[5])) if len(vals) > 5 and vals[5] else 0
        except: q_7d = 0
        days_silent = 999
        if last_seen:
            try:
                days_silent = (_today - _dt.strptime(last_seen, "%Y-%m-%d").date()).days
            except: pass
        bucket = vals[7] if len(vals) > 7 else ""
        bl = bucket.lower()
        if "sales" in bl or "ready" in bl: cls = "Sales-Ready"
        elif "power" in bl:                cls = "Power User"
        elif "explor" in bl:               cls = "Explorer"
        elif "block" in bl:                cls = "Blocked"
        else:                              cls = "Low Usage"
        if days_silent <= 1:   trend = "Highly Active"
        elif days_silent <= 7: trend = "Active"
        elif days_silent <= 30:trend = "Going Quiet"
        else:                  trend = "Churned"
        sellers.append({
            "seller_id": sid, "email": email,
            "q_recent": q_7d, "q_total": q_total,
            "last_active": last_seen, "days_silent": days_silent,
            "trend": trend, "classification": cls,
            "q_summary": vals[6] if len(vals) > 6 else "",
            "a_summary": vals[9] if len(vals) > 9 else "",
            "action":    vals[8] if len(vals) > 8 else "",
        })

# Enrich sellers with user/query data from eval sheet (vectorised — no iterrows)
if not eval_processed.empty and sellers and "_email" in eval_processed.columns:
    _ev = eval_processed[["_seller", "_email", "_date"]].copy()
    _ev = _ev[_ev["_seller"].notna() & _ev["_email"].notna()]
    _ev = _ev[(_ev["_seller"] != "nan") & (_ev["_email"] != "nan") & (_ev["_email"] != "")]

    # Build seller → {email → {count, dates}} map via groupby
    for sid, grp in _ev.groupby("_seller", sort=False):
        seller_users_map[sid] = {}
        for em, eg in grp.groupby("_email", sort=False):
            dates = eg["_date"].dropna().dt.strftime("%Y-%m-%d").tolist()
            seller_users_map[sid][em] = {"count": len(eg), "dates": dates}

    for s in sellers:
        sid = s["seller_id"]
        if sid in seller_users_map:
            info = seller_users_map[sid]
            s["user_count"]   = len(info)
            s["all_emails"]   = list(info.keys())
        else:
            s["user_count"]   = 1
            s["all_emails"]   = [s["email"]]
else:
    # No eval data — give every seller safe defaults
    for s in sellers:
        s.setdefault("user_count", 1)
        s.setdefault("all_emails", [s.get("email", "")])

# ── Period filter helper ──────────────────────────────────────────────────────

def apply_period(df: pd.DataFrame, period: str, date_col: str = "_date"):
    if df.empty or date_col not in df.columns:
        return df
    today_ts   = df[date_col].max()
    data_start = df[date_col].min()
    cutoffs    = {"1W": today_ts - pd.Timedelta(days=7),
                  "1M": today_ts - pd.Timedelta(days=30),
                  "3M": today_ts - pd.Timedelta(days=90)}
    if period in cutoffs:
        cutoff = max(cutoffs[period], data_start)
        return df[df[date_col] >= cutoff]
    return df

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_home, tab_accounts, tab_ask = st.tabs(["🏠 Home", "👥 Accounts", "💬 Ask Hoppr"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HOME
# ══════════════════════════════════════════════════════════════════════════════

with tab_home:

    # ── KPI cards ─────────────────────────────────────────────────────────────
    if not daily.empty:
        today_ts  = daily["date"].max()
        this_week = daily[daily["date"] >= today_ts - pd.Timedelta(days=7)]
        last_week = daily[(daily["date"] >= today_ts - pd.Timedelta(days=14)) &
                          (daily["date"] <  today_ts - pd.Timedelta(days=7))]

        def safe_delta(a, b):
            return f"{((a - b) / b * 100):+.0f}%" if b else None

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            tw, lw = this_week["total_queries"].sum(), last_week["total_queries"].sum()
            st.metric("Queries (7d)", f"{tw:,}", safe_delta(tw, lw))
        with c2:
            tw, lw = this_week["unique_users"].sum(), last_week["unique_users"].sum()
            st.metric("Unique Users (7d)", f"{tw:,}", safe_delta(tw, lw))
        with c3:
            tw, lw = this_week["unique_sellers"].sum(), last_week["unique_sellers"].sum()
            st.metric("Unique Sellers (7d)", f"{tw:,}", safe_delta(tw, lw))
        with c4:
            tw, lw = this_week["new_signups"].sum(), last_week["new_signups"].sum()
            st.metric("New Signups (7d)", f"{tw:,}", safe_delta(tw, lw))

    # ── Period selector ───────────────────────────────────────────────────────
    period = st.radio("Period", ["1W", "1M", "3M", "All"], index=1,
                      horizontal=True, key="hoppr_period")

    if not daily.empty:
        today_ts   = daily["date"].max()
        data_start = daily["date"].min()
        cutoffs = {"1W": today_ts - pd.Timedelta(days=7),
                   "1M": today_ts - pd.Timedelta(days=30),
                   "3M": today_ts - pd.Timedelta(days=90)}
        if period in cutoffs:
            cutoff   = max(cutoffs[period], data_start)
            daily_f  = daily[daily["date"] >= cutoff]
            country_f = country[country["date"] >= cutoff] \
                if not country.empty and "date" in country.columns else country
        else:
            daily_f, country_f = daily, country

        f_start = daily_f["date"].min().strftime("%d %b %Y").lstrip("0") if not daily_f.empty else "—"
        f_end   = daily_f["date"].max().strftime("%d %b %Y").lstrip("0") if not daily_f.empty else "—"
        st.caption(f"📅 {f_start} → {f_end} · {len(daily_f)} days")

        # Trend chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_f["date"], y=daily_f["total_queries"],
                                 mode="lines+markers", name="Queries",
                                 line=dict(color="#4F46E5", width=2)))
        fig.add_trace(go.Bar(x=daily_f["date"], y=daily_f["unique_sellers"],
                             name="Unique Sellers", marker_color="#7C3AED", opacity=0.5))
        fig.add_trace(go.Scatter(x=daily_f["date"], y=daily_f["new_signups"],
                                 mode="lines+markers", name="New Signups",
                                 line=dict(color="#10B981", dash="dot")))
        fig.update_layout(height=340, template="plotly_dark",
                          margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # Country breakdown
        if not country_f.empty:
            ca = (country_f.groupby("country")["total_queries"].sum()
                  .reset_index()
                  .query("country != 'Unknown'")
                  .sort_values("total_queries", ascending=True))
            if not ca.empty:
                fig_c = px.bar(ca, x="total_queries", y="country", orientation="h",
                               color_discrete_sequence=["#4F46E5"],
                               labels={"total_queries": "Queries", "country": ""},
                               title="By Country")
                fig_c.update_layout(height=220, template="plotly_dark",
                                    margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_c, use_container_width=True)
    else:
        st.warning("No daily usage data available.")

    # ── What sellers are asking about ────────────────────────────────────────
    if not eval_processed.empty:
        st.markdown("---")
        st.markdown("### 📊 What Sellers Are Asking About")

        ev_f = apply_period(eval_processed, period)

        if not ev_f.empty:
            bucket_rows = [
                {"bucket": b}
                for buckets in ev_f["_buckets"]
                for b in buckets
            ]
            if bucket_rows:
                bc = pd.DataFrame(bucket_rows)["bucket"].value_counts().reset_index()
                bc.columns = ["Question Type", "Count"]

                fig_b = px.bar(bc, x="Count", y="Question Type", orientation="h",
                               color="Question Type",
                               color_discrete_sequence=px.colors.qualitative.Bold,
                               labels={"Count": "Queries", "Question Type": ""})
                fig_b.update_layout(height=400, template="plotly_dark",
                                    margin=dict(l=20, r=20, t=10, b=20),
                                    showlegend=False,
                                    yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_b, use_container_width=True)

    # ── Data accuracy queries ────────────────────────────────────────────────
    if not eval_processed.empty:
        st.markdown("---")
        st.markdown("### ⚠️ Data Accuracy Issues")
        st.caption("Questions where sellers flagged data gaps, mismatches, or incorrect values")

        acc_all = eval_processed[eval_processed["_is_accuracy"]]
        acc_f   = apply_period(acc_all, period) if not acc_all.empty else acc_all

        if acc_f.empty:
            st.success("No data accuracy queries in this period.")
        else:
            a1, a2, a3 = st.columns(3)
            with a1: st.metric("Accuracy Queries", len(acc_f))
            with a2: st.metric("Sellers Affected", acc_f["_seller"].nunique())
            with a3:
                total_f = len(apply_period(eval_processed, period))
                pct = f"{len(acc_f)/total_f*100:.1f}%" if total_f else "—"
                st.metric("% of All Queries", pct)

            view = st.radio("View as", ["Over Time", "By Account"], horizontal=True, key="acc_view")

            if view == "Over Time":
                weekly = acc_f.groupby("_week").size().reset_index(name="Queries")
                weekly.columns = ["Week", "Queries"]
                fig_a = px.bar(weekly, x="Week", y="Queries",
                               color_discrete_sequence=["#EF4444"])
                fig_a.update_layout(height=260, template="plotly_dark",
                                    margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_a, use_container_width=True)
            else:
                by_acct = (acc_f.groupby("_seller")
                           .agg(Queries=("_question", "count"),
                                Example=("_question", lambda x: x.iloc[0][:100]))
                           .reset_index()
                           .sort_values("Queries", ascending=False)
                           .head(20))
                by_acct.columns = ["Seller", "Accuracy Queries", "Example Question"]
                st.dataframe(by_acct, use_container_width=True, hide_index=True)

            with st.expander(f"Show all {len(acc_f)} accuracy queries"):
                show = acc_f[["_date", "_seller", "_email", "_question"]].copy()
                show.columns = ["Date", "Seller", "Email", "Question"]
                show["Question"] = show["Question"].str[:200]
                st.dataframe(show.sort_values("Date", ascending=False),
                             use_container_width=True, hide_index=True)

    # ── Acquisition funnel ───────────────────────────────────────────────────
    if not raw_funnel.empty:
        with st.expander("🔄 Acquisition Funnel", expanded=False):
            def _si(df, r, c):
                try: return int(float(str(df.iloc[r, c]).replace(",", "").strip()))
                except: return 0
            chat_visits  = _si(raw_funnel, 1, 7)
            unique_users = _si(raw_funnel, 4, 8)
            signups      = _si(raw_funnel, 9, 7)
            connect_flow = _si(raw_funnel, 13, 6)
            connected    = _si(raw_funnel, 17, 5)
            sv = [(s, v) for s, v in zip(
                ["Chat Visits", "Unique Users", "Signups", "Connect Flow", "Connected"],
                [chat_visits, unique_users, signups, connect_flow, connected]
            ) if v > 0]
            if sv:
                ss, vv = zip(*sv)
                fig_f = go.Figure(go.Funnel(
                    y=list(ss), x=list(vv),
                    textinfo="value+percent initial",
                    marker=dict(color=["#4F46E5", "#6366F1", "#7C3AED", "#8B5CF6", "#10B981"]),
                ))
                fig_f.update_layout(height=300, template="plotly_dark",
                                    margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_f, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ACCOUNTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_accounts:

    if not sellers:
        st.warning("No account data available.")
    else:
        sellers_df = pd.DataFrame(sellers)
        if "user_count" not in sellers_df.columns:
            sellers_df["user_count"] = 1

        # ── KPIs ──────────────────────────────────────────────────────────
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1: st.metric("Total Sellers", len(sellers_df))
        with k2: st.metric("Total Users", int(sellers_df["user_count"].sum()))
        with k3: st.metric("Active (7d)", len(sellers_df[sellers_df["days_silent"] <= 7]))
        with k4: st.metric("Power Users", len(sellers_df[sellers_df["classification"] == "Power User"]))
        with k5: st.metric("Sales-Ready", len(sellers_df[sellers_df["classification"] == "Sales-Ready"]))
        with k6: st.metric("Going Quiet", len(sellers_df[sellers_df["trend"] == "Going Quiet"]),
                            delta_color="inverse")

        # ── Filters ───────────────────────────────────────────────────────
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            classes = sorted(sellers_df["classification"].unique())
            sel_cls = st.multiselect("Classification", classes, default=list(classes), key="acct_class")
        with fc2:
            trends_l = sorted(sellers_df["trend"].unique())
            sel_tr = st.multiselect("Trend", trends_l, default=list(trends_l), key="acct_trend")
        with fc3:
            search = st.text_input("Search (ID or email)", "", key="acct_search")

        filt = sellers_df[
            sellers_df["classification"].isin(sel_cls) &
            sellers_df["trend"].isin(sel_tr)
        ]
        if search:
            filt = filt[
                filt["seller_id"].str.contains(search, case=False, na=False) |
                filt["email"].str.contains(search, case=False, na=False)
            ]

        # ── Color helpers ──────────────────────────────────────────────────
        def cls_color(v):
            return {"Sales-Ready": "background-color:#065F46;color:white",
                    "Power User":  "background-color:#1E40AF;color:white",
                    "Explorer":    "background-color:#92400E;color:white",
                    "Low Usage":   "background-color:#78350F;color:white",
                    "Blocked":     "background-color:#7F1D1D;color:white"}.get(v, "")

        def tr_color(v):
            return {"Highly Active": "color:#10B981", "Active": "color:#06B6D4",
                    "Going Quiet":   "color:#F59E0B", "Churned": "color:#EF4444"}.get(v, "")

        disp = filt[["seller_id", "email", "user_count", "q_total", "q_recent",
                      "last_active", "days_silent", "trend", "classification"]].copy()
        disp = disp.sort_values("days_silent")
        st.dataframe(
            disp.rename(columns={
                "seller_id": "Seller", "email": "Email", "user_count": "Users",
                "q_total": "Total Q", "q_recent": "Q (7d)",
                "last_active": "Last Active", "days_silent": "Days Silent",
                "trend": "Trend", "classification": "Class",
            }).style.map(cls_color, subset=["Class"]).map(tr_color, subset=["Trend"]),
            use_container_width=True, height=380, hide_index=True,
        )

        # ── Account Deep Dive ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🔍 Account Detail")

        dd_col1, dd_col2 = st.columns([3, 1])
        with dd_col1:
            if not eval_processed.empty:
                sq = eval_processed["_seller"].value_counts().to_dict()
                dd_opts = [f"{sid} ({sq[sid]}Q)"
                           for sid in sorted(sq, key=lambda x: -sq[x])]
            else:
                dd_opts = [f"{s['seller_id']} ({s['q_total']}Q)"
                           for s in sorted(sellers, key=lambda x: -x.get("q_total", 0))]
            sel_dd = st.selectbox("Select account", dd_opts, key="dd_seller")

        with dd_col2:
            dd_period = st.radio("Usage period", ["1W", "1M", "3M", "All"],
                                 index=2, horizontal=False, key="dd_period")

        if sel_dd and not eval_processed.empty:
            sel_sid = sel_dd.split(" (")[0]
            acct_rows = eval_processed[eval_processed["_seller"] == sel_sid].copy()

            # Get User_State metadata
            us = {}
            if not raw_user_state.empty:
                for i in range(len(raw_user_state)):
                    v = [str(x).strip() if pd.notna(x) else "" for x in raw_user_state.iloc[i].values]
                    if v[0] == sel_sid:
                        us = {"summary": v[6] if len(v) > 6 else "",
                              "bucket":  v[7] if len(v) > 7 else "",
                              "action":  v[8] if len(v) > 8 else "",
                              "reason":  v[9] if len(v) > 9 else ""}
                        break

            emails     = [e for e in acct_rows["_email"].unique() if e and e != "nan"]
            all_dates  = sorted(acct_rows["_date"].dropna().unique())
            first_date = str(all_dates[0])[:10]  if all_dates else "—"
            last_date  = str(all_dates[-1])[:10] if all_dates else "—"

            # KPIs
            kk1, kk2, kk3, kk4, kk5 = st.columns(5)
            with kk1: st.metric("Total Queries", len(acct_rows))
            with kk2: st.metric("Users", len(emails))
            with kk3: st.metric("First Active", first_date)
            with kk4: st.metric("Last Active", last_date)
            with kk5: st.metric("Classification", us.get("bucket", "—") or "—")

            if us.get("action"):
                st.info(f"**Recommended Action:** {us['action'][:400]}")

            # ── Usage over time chart ─────────────────────────────────────
            acct_f = apply_period(acct_rows, dd_period)

            if not acct_f.empty:
                st.markdown("#### 📈 Usage Over Time")
                daily_s = acct_f.groupby("_date").agg(
                    Queries=("_question", "count"),
                    Users=("_email", "nunique"),
                ).reset_index().rename(columns={"_date": "Date"})

                fig_u = go.Figure()
                fig_u.add_trace(go.Bar(x=daily_s["Date"], y=daily_s["Queries"],
                                       name="Queries", marker_color="#4F46E5"))
                fig_u.add_trace(go.Scatter(x=daily_s["Date"], y=daily_s["Users"],
                                           name="Users", mode="lines+markers",
                                           line=dict(color="#10B981", width=2),
                                           yaxis="y2"))
                fig_u.update_layout(
                    height=260, template="plotly_dark",
                    margin=dict(l=20, r=50, t=20, b=20),
                    yaxis=dict(title="Queries"),
                    yaxis2=dict(title="Users", overlaying="y", side="right"),
                    legend=dict(orientation="h", y=1.12),
                )
                st.plotly_chart(fig_u, use_container_width=True)

            # ── Users table ───────────────────────────────────────────────
            st.markdown("#### 👥 Users")
            user_rows = []
            for em in emails:
                em_rows  = acct_rows[acct_rows["_email"] == em]
                em_dates = sorted(em_rows["_date"].dropna().unique())
                all_tags = [t for q in em_rows["_question"] for t in classify_question(q)]
                top_types = pd.Series(all_tags).value_counts().index.tolist()[:3]
                user_rows.append({
                    "Email":          em,
                    "Queries":        len(em_rows),
                    "Question Types": ", ".join(top_types),
                    "First Active":   str(em_dates[0])[:10]  if em_dates else "—",
                    "Last Active":    str(em_dates[-1])[:10] if em_dates else "—",
                })
            user_rows.sort(key=lambda x: -x["Queries"])
            if user_rows:
                st.dataframe(pd.DataFrame(user_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No user email data found for this account.")

            # ── AI analysis ───────────────────────────────────────────────
            if us.get("summary") or us.get("reason"):
                st.markdown("#### 🧠 AI Analysis")
                col_s, col_a = st.columns(2)
                with col_s:
                    st.markdown("**What they're asking about:**")
                    st.markdown(us.get("summary", "—")[:2000])
                with col_a:
                    st.markdown("**Answer quality:**")
                    st.markdown(us.get("reason", "—")[:2000])

            # ── Query timeline ────────────────────────────────────────────
            st.markdown("#### 📋 Query Timeline")
            if acct_f.empty:
                st.info("No queries in this period. Try a wider time window.")
            timeline = acct_f.sort_values("_date", ascending=False).head(100)

            for _, qrow in timeline.iterrows():
                dt       = str(qrow["_date"])[:10]
                em       = str(qrow["_email"])
                question = str(qrow["_question"])[:200]
                answer   = str(qrow["_answer"])
                has_data = any(c in answer for c in ["📊", "|", "%", "table"])
                failed   = any(w in answer.lower()
                               for w in ["unable", "don't have", "not available",
                                         "cannot provide", "no data"])
                acc_flag = "🔴 " if is_accuracy(question) else ""
                status   = "⚠️" if failed else ("✅" if has_data else "➡️")
                em_short = em.split("@")[0] if "@" in em else em
                with st.expander(f"{acc_flag}{status} {dt} — **{em_short}** — {question}"):
                    st.markdown(f"**Q:** {question}")
                    st.markdown("**A:**")
                    st.markdown(answer[:800] if answer else "No answer recorded")

            if len(acct_f) > 100:
                st.caption(f"Showing most recent 100 of {len(acct_f)} queries in this period.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ASK HOPPR
# ══════════════════════════════════════════════════════════════════════════════

with tab_ask:
    st.markdown("### 💬 Ask Hoppr")
    st.caption("Ask anything about Hoppr usage, seller health, query trends, or data quality.")

    # Build context for system prompt
    @st.cache_data(ttl=1800)
    def _build_context(_daily, _sellers_list, _eval_df):
        lines = []

        if not _daily.empty:
            lines.append(f"DATA RANGE: {_daily['date'].min().date()} → {_daily['date'].max().date()}")
            lines.append(f"TOTAL QUERIES (all time): {int(_daily['total_queries'].sum())}")
            today_ts   = _daily["date"].max()
            wk  = _daily[_daily["date"] >= today_ts - pd.Timedelta(days=7)]
            pwk = _daily[(_daily["date"] >= today_ts - pd.Timedelta(days=14)) &
                         (_daily["date"] <  today_ts - pd.Timedelta(days=7))]
            wq, pq = int(wk["total_queries"].sum()), int(pwk["total_queries"].sum())
            wow = f"{(wq-pq)/pq*100:+.0f}%" if pq else "N/A"
            lines.append(f"LAST 7 DAYS: {wq} queries ({wow} WoW), "
                         f"{int(wk['unique_sellers'].sum())} sellers, {int(wk['unique_users'].sum())} users")

        if _sellers_list:
            sdf = pd.DataFrame(_sellers_list)
            lines.append(f"\nSELLERS: {len(sdf)} total sellers tracked")
            lines.append(f"  Active ≤7d:  {len(sdf[sdf['days_silent'] <= 7])}")
            lines.append(f"  Power Users: {len(sdf[sdf['classification'] == 'Power User'])}")
            lines.append(f"  Sales-Ready: {len(sdf[sdf['classification'] == 'Sales-Ready'])}")
            lines.append(f"  Going Quiet: {len(sdf[sdf['trend'] == 'Going Quiet'])}")
            lines.append(f"  Churned:     {len(sdf[sdf['trend'] == 'Churned'])}")
            top5 = sdf.nlargest(5, "q_total")
            lines.append(f"\nTOP 5 SELLERS BY QUERY VOLUME:")
            for _, r in top5.iterrows():
                lines.append(f"  {r['seller_id']} ({r['email']}): {r['q_total']}Q total, "
                             f"{r['classification']}, {r['trend']}, {r['days_silent']}d silent")
            going_quiet = sdf[sdf["trend"].isin(["Going Quiet", "Churned"])].nlargest(5, "q_total")
            if not going_quiet.empty:
                lines.append(f"\nAT-RISK SELLERS (going quiet or churned, by query volume):")
                for _, r in going_quiet.iterrows():
                    lines.append(f"  {r['seller_id']} ({r['email']}): {r['days_silent']}d silent, {r['q_total']}Q total")

        if not _eval_df.empty and "_buckets" in _eval_df.columns:
            from collections import Counter
            all_b = [b for bl in _eval_df["_buckets"] for b in bl]
            counts = Counter(all_b).most_common(10)
            lines.append(f"\nQUESTION TYPES (all time):")
            for bucket, cnt in counts:
                lines.append(f"  {bucket}: {cnt}")

        if not _eval_df.empty and "_is_accuracy" in _eval_df.columns:
            acc = int(_eval_df["_is_accuracy"].sum())
            tot = len(_eval_df)
            lines.append(f"\nDATA ACCURACY ISSUES: {acc} queries ({acc/tot*100:.1f}% of total)")
            if acc:
                top_acc = _eval_df[_eval_df["_is_accuracy"]]["_seller"].value_counts().head(5)
                lines.append("  Top sellers with accuracy queries:")
                for sid, cnt in top_acc.items():
                    lines.append(f"    {sid}: {cnt}")

        return "\n".join(lines)

    ctx = _build_context(
        daily if not daily.empty else pd.DataFrame(),
        sellers,
        eval_processed if not eval_processed.empty else pd.DataFrame(),
    )

    SYSTEM_PROMPT = f"""You are Ask Hoppr — an AI analyst embedded in the Graas Command Center.
You have access to live Hoppr usage data. Answer questions about seller usage, query trends, data quality, and account health concisely and with numbers.
Use bullet points. Cite specific sellers or metrics when relevant. If something is outside the data, say so.

Current data snapshot:
---
{ctx}
---"""

    # ── Seller-specific query context (injected dynamically) ──────────────────
    def _get_seller_detail_context(seller_id: str, eval_df: pd.DataFrame) -> str:
        """Return the full query log for a specific seller, broken down by user email."""
        if eval_df.empty or "_seller" not in eval_df.columns:
            return ""
        rows = eval_df[eval_df["_seller"] == seller_id].sort_values("_date")
        if rows.empty:
            return ""

        lines = [f"\n===== FULL QUERY LOG FOR SELLER: {seller_id} ====="]
        lines.append(f"Total queries in dataset: {len(rows)}")

        # Per-email breakdown
        if "_email" in rows.columns:
            email_groups = rows.groupby("_email", sort=False)
            for email, grp in email_groups:
                em = str(email)
                if not em or em == "nan":
                    continue
                grp = grp.sort_values("_date")
                lines.append(f"\n  --- User: {em} ({len(grp)} queries) ---")
                for _, r in grp.iterrows():
                    dt = str(r["_date"])[:10]
                    q  = str(r["_question"])[:400]
                    bucket_tags = ", ".join(classify_question(q))
                    acc_flag = " [DATA ACCURACY ISSUE]" if is_accuracy(q) else ""
                    lines.append(f"    [{dt}] [{bucket_tags}]{acc_flag} {q}")
        else:
            for _, r in rows.iterrows():
                dt = str(r["_date"])[:10]
                q  = str(r["_question"])[:400]
                lines.append(f"  [{dt}] {q}")

        lines.append("===== END SELLER LOG =====")
        return "\n".join(lines)

    def _detect_seller_ids(text: str, known_sellers: list) -> list:
        """Find any known seller IDs mentioned in the user's question."""
        text_upper = text.upper()
        found = []
        for s in known_sellers:
            sid = s.get("seller_id", "")
            if sid and len(sid) >= 3 and sid in text_upper:
                found.append(sid)
        return list(set(found))

    if "hoppr_chat" not in st.session_state:
        st.session_state.hoppr_chat = []

    for msg in st.session_state.hoppr_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about Hoppr..."):
        st.session_state.hoppr_chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                import anthropic as _anthropic
                # Prefer st.secrets (authoritative on Streamlit Cloud)
                try:
                    api_key = st.secrets["ANTHROPIC_API_KEY"]
                except Exception:
                    api_key = os.getenv("ANTHROPIC_API_KEY", "")
                if not api_key:
                    response = "⚠️ ANTHROPIC_API_KEY not configured."
                else:
                    # Detect if question is about a specific seller → inject full query log
                    mentioned_sellers = _detect_seller_ids(prompt, sellers)
                    extra_ctx = ""
                    if mentioned_sellers and not eval_processed.empty:
                        for sid in mentioned_sellers[:3]:  # cap at 3 sellers
                            extra_ctx += _get_seller_detail_context(sid, eval_processed)

                    dynamic_system = SYSTEM_PROMPT
                    if extra_ctx:
                        dynamic_system += f"\n\nFULL QUERY DATA FOR MENTIONED SELLERS (use this to answer the question):\n{extra_ctx}"

                    ai = _anthropic.Anthropic(api_key=api_key)
                    with st.spinner("Thinking…"):
                        result = ai.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=2048,
                            system=dynamic_system,
                            messages=[{"role": m["role"], "content": m["content"]}
                                      for m in st.session_state.hoppr_chat],
                        )
                    response = result.content[0].text
            except Exception as e:
                response = f"Error: {e}"

            st.markdown(response)
            st.session_state.hoppr_chat.append({"role": "assistant", "content": response})

    if st.session_state.hoppr_chat:
        if st.button("Clear chat", key="clear_hoppr"):
            st.session_state.hoppr_chat = []
            st.rerun()
