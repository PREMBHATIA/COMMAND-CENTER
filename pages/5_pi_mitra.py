"""All-e: PI Mitra Connect — Retailer Ordering Agent Dashboard."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

_env_path = str(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(_env_path, override=True)

st.set_page_config(page_title="PI Mitra Connect | Graas", page_icon="🌿", layout="wide")
st.markdown("## 🌿 All-e: PI Mitra Connect")
st.caption("WhatsApp B2B dealer ordering agent for PI Industries | Source: PI Bot Analytics Sheet")
st.info("⚠️ **Note:** PI is mid-SAP HANA migration — ordering paused until next week. Apr numbers reflect this, not a usage drop.")

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING — from Google Sheet
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def load_pi_bot_data():
    """Load all tabs from the PI Bot analytics sheet."""
    from services.sheets_client import fetch_sheet_tab
    sheet_id = os.getenv("PI_BOT_SHEET_ID", "")
    if not sheet_id:
        return {}

    tabs = {
        "core": "📊 Core Metrics",
        "monthly": "📅 Monthly Breakdown",
        "weekly": "📈 Weekly Trend",
        "funnel": "🔽 User Funnel",
        "orders": "📦 Order Distribution",
        "input": "🖼 Input Methods",
        "sessions": "🔄 Session Analysis",
        "products": "🌿 Top Products",
    }
    data = {}
    for key, tab_name in tabs.items():
        try:
            data[key] = fetch_sheet_tab(sheet_id, tab_name)
        except Exception:
            pass
    return data


def safe_int(v):
    try:
        return int(str(v).strip().replace(",", "").replace("%", ""))
    except (ValueError, TypeError):
        return 0


def safe_pct(v):
    s = str(v).strip().replace("%", "")
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


pi_data = load_pi_bot_data()

if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

if not pi_data:
    st.warning("No PI Bot data. Check PI_BOT_SHEET_ID in .env.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# 1. CORE METRICS — KPI cards
# ══════════════════════════════════════════════════════════════════════════════

core = pi_data.get("core", pd.DataFrame())

def _core_val(metric_name):
    """Get value from core metrics by metric name."""
    if core.empty:
        return "", ""
    for i in range(len(core)):
        row = core.iloc[i]
        label = str(row.iloc[0]).strip()
        if label.lower() == metric_name.lower():
            val = str(row.iloc[1]).strip() if len(row) > 1 else ""
            vs_pilot = str(row.iloc[3]).strip() if len(row) > 3 else ""
            if vs_pilot == "nan":
                vs_pilot = ""
            return val, vs_pilot
    return "", ""


# Parse core metrics into sections
core_sections = {}
current_section = ""
if not core.empty:
    for i in range(len(core)):
        row = core.iloc[i]
        first = str(row.iloc[0]).strip()
        # Section headers: SCALE, EFFICIENCY, ENGAGEMENT, GROWTH
        if first.isupper() and len(first) < 20 and first not in ("", "Metric"):
            current_section = first
            continue
        if first and first != "Metric" and current_section:
            val = str(row.iloc[1]).strip() if len(row) > 1 else ""
            pct = str(row.iloc[2]).strip() if len(row) > 2 else ""
            vs_pilot = str(row.iloc[3]).strip() if len(row) > 3 else ""
            if val == "nan":
                val = ""
            if pct == "nan":
                pct = ""
            if vs_pilot == "nan":
                vs_pilot = ""
            if current_section not in core_sections:
                core_sections[current_section] = []
            core_sections[current_section].append({
                "metric": first, "value": val, "pct": pct, "vs_pilot": vs_pilot,
            })

# Top KPI cards
st.markdown("### Key Metrics")

scale = core_sections.get("SCALE", [])
efficiency = core_sections.get("EFFICIENCY", [])
engagement = core_sections.get("ENGAGEMENT", [])

# Row 1: Scale
if scale:
    cols = st.columns(len(scale))
    for col, m in zip(cols, scale):
        with col:
            delta = m["vs_pilot"] if m["vs_pilot"] else None
            st.metric(m["metric"], m["value"], delta)

# Row 2: Efficiency + Engagement
combined = efficiency + engagement
if combined:
    cols = st.columns(min(len(combined), 6))
    for col, m in zip(cols, combined[:6]):
        with col:
            label = m["metric"]
            val = m["value"]
            if m["pct"] and m["pct"] != "—":
                val = f'{m["value"]} ({m["pct"]})'
            delta = m["vs_pilot"] if m["vs_pilot"] else None
            st.metric(label, val, delta)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 2. MONTHLY BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════════

monthly = pi_data.get("monthly", pd.DataFrame())

if not monthly.empty and len(monthly) > 1:
    st.markdown("### 📅 Monthly Breakdown")

    # Parse — row 0 is header
    m_headers = [str(c).strip() for c in monthly.iloc[0]]
    m_data = []
    for i in range(1, len(monthly)):
        row = monthly.iloc[i]
        month_name = str(row.iloc[0]).strip()
        if not month_name or month_name == "nan":
            continue
        entry = {"Month": month_name}
        for j in range(1, len(m_headers)):
            if j < len(row):
                entry[m_headers[j]] = str(row.iloc[j]).strip()
        m_data.append(entry)

    if m_data:
        m_df = pd.DataFrame(m_data)
        # Display as styled table
        st.dataframe(m_df, use_container_width=True, hide_index=True)

        # Bar chart — orders + new users by month
        chart_months = [r["Month"] for r in m_data if r["Month"] != "TOTAL"]
        chart_orders = [safe_int(r.get("Orders Placed", 0)) for r in m_data if r["Month"] != "TOTAL"]
        chart_users = [safe_int(r.get("New Users", 0)) for r in m_data if r["Month"] != "TOTAL"]
        chart_conv = [safe_pct(r.get("Conv Rate", 0)) for r in m_data if r["Month"] != "TOTAL"]

        fig_m = go.Figure()
        fig_m.add_trace(go.Bar(x=chart_months, y=chart_users, name="New Users", marker_color="#3B82F6"))
        fig_m.add_trace(go.Bar(x=chart_months, y=chart_orders, name="Orders", marker_color="#10B981"))
        fig_m.add_trace(go.Scatter(
            x=chart_months, y=chart_conv, name="Conv %", yaxis="y2",
            mode="lines+markers", line=dict(color="#F59E0B", width=2), marker=dict(size=8),
        ))
        fig_m.update_layout(
            barmode="group", height=300, template="plotly_dark",
            margin=dict(l=20, r=40, t=10, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis2=dict(title="Conv %", overlaying="y", side="right", range=[0, 100]),
        )
        st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 3. WEEKLY TREND
# ══════════════════════════════════════════════════════════════════════════════

weekly = pi_data.get("weekly", pd.DataFrame())

if not weekly.empty and len(weekly) > 1:
    st.markdown("### 📈 Weekly Trend")

    w_data = []
    for i in range(1, len(weekly)):
        row = weekly.iloc[i]
        week = str(row.iloc[0]).strip()
        if not week or week == "nan":
            continue
        w_data.append({
            "Week": week,
            "Period": str(row.iloc[1]).strip() if len(row) > 1 else "",
            "New Users": safe_int(row.iloc[2]) if len(row) > 2 else 0,
            "Orders": safe_int(row.iloc[3]) if len(row) > 3 else 0,
            "Cumul Users": safe_int(row.iloc[4]) if len(row) > 4 else 0,
            "Cumul Orders": safe_int(row.iloc[5]) if len(row) > 5 else 0,
        })

    if w_data:
        w_df = pd.DataFrame(w_data)

        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(x=w_df["Week"], y=w_df["New Users"], name="New Users", marker_color="#3B82F6"))
        fig_w.add_trace(go.Bar(x=w_df["Week"], y=w_df["Orders"], name="Orders", marker_color="#10B981"))
        fig_w.add_trace(go.Scatter(
            x=w_df["Week"], y=w_df["Cumul Orders"], name="Cumul Orders", yaxis="y2",
            mode="lines+markers", line=dict(color="#F59E0B", dash="dash"), marker=dict(size=6),
        ))
        fig_w.update_layout(
            barmode="group", height=320, template="plotly_dark",
            margin=dict(l=20, r=40, t=10, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis2=dict(title="Cumulative", overlaying="y", side="right"),
        )
        st.plotly_chart(fig_w, use_container_width=True)

        with st.expander("Weekly data table"):
            st.dataframe(w_df, use_container_width=True, hide_index=True)

    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 4. USER FUNNEL + SESSION ANALYSIS (side by side)
# ══════════════════════════════════════════════════════════════════════════════

funnel = pi_data.get("funnel", pd.DataFrame())
sessions = pi_data.get("sessions", pd.DataFrame())

col_funnel, col_sessions = st.columns(2)

with col_funnel:
    if not funnel.empty and len(funnel) > 1:
        st.markdown("### 🔽 User Funnel")

        funnel_data = []
        for i in range(1, len(funnel)):
            row = funnel.iloc[i]
            outcome = str(row.iloc[0]).strip()
            if not outcome or outcome == "nan":
                continue
            users = safe_int(row.iloc[1]) if len(row) > 1 else 0
            pct = str(row.iloc[2]).strip() if len(row) > 2 else ""
            vs_pilot = str(row.iloc[3]).strip() if len(row) > 3 else ""
            if pct == "nan":
                pct = ""
            if vs_pilot == "nan":
                vs_pilot = ""
            funnel_data.append({
                "outcome": outcome.strip().lstrip("  "),
                "users": users, "pct": pct, "vs_pilot": vs_pilot,
            })

        # Funnel bar chart
        if funnel_data:
            f_labels = [f["outcome"] for f in funnel_data]
            f_values = [f["users"] for f in funnel_data]
            f_colors = ["#3B82F6", "#10B981", "#EF4444", "#F59E0B", "#EF4444", "#6B7280"]

            fig_f = go.Figure(go.Bar(
                y=f_labels, x=f_values, orientation="h",
                text=[f'{v} ({f["pct"]})' if f["pct"] else str(v) for v, f in zip(f_values, funnel_data)],
                textposition="outside",
                marker_color=f_colors[:len(f_labels)],
            ))
            fig_f.update_layout(
                height=280, template="plotly_dark",
                margin=dict(l=10, r=80, t=10, b=10),
                yaxis=dict(autorange="reversed"),
                xaxis=dict(visible=False),
            )
            st.plotly_chart(fig_f, use_container_width=True)

            # vs Pilot notes
            for f in funnel_data:
                if f["vs_pilot"]:
                    st.caption(f'{f["outcome"]}: {f["vs_pilot"]}')

with col_sessions:
    if not sessions.empty and len(sessions) > 1:
        st.markdown("### 🔄 Session Analysis")

        sess_data = []
        sess_notes = []
        for i in range(1, len(sessions)):
            row = sessions.iloc[i]
            segment = str(row.iloc[0]).strip()
            if not segment or segment == "nan":
                continue
            # Check if it's a note row (no numeric data)
            users = safe_int(row.iloc[1]) if len(row) > 1 else 0
            if users == 0 and "median" in segment.lower():
                sess_notes.append(segment)
                continue
            if users == 0 and "total" in segment.lower():
                sess_notes.append(f'{segment}: {str(row.iloc[1]).strip() if len(row) > 1 else ""}')
                continue

            pct = str(row.iloc[2]).strip() if len(row) > 2 else ""
            converters = safe_int(row.iloc[3]) if len(row) > 3 else 0
            conv_rate = str(row.iloc[4]).strip() if len(row) > 4 else ""
            vs_pilot = str(row.iloc[5]).strip() if len(row) > 5 else ""
            if pct == "nan":
                pct = ""
            if conv_rate == "nan":
                conv_rate = ""
            if vs_pilot == "nan":
                vs_pilot = ""

            sess_data.append({
                "Segment": segment, "Users": users, "%": pct,
                "Converters": converters, "Conv Rate": conv_rate, "vs Pilot": vs_pilot,
            })

        if sess_data:
            s_df = pd.DataFrame(sess_data)
            st.dataframe(s_df, use_container_width=True, hide_index=True)

            # Highlight multi-session conversion
            for s in sess_data:
                if "multi" in s["Segment"].lower() and s["vs Pilot"]:
                    st.success(f'**{s["Segment"]}**: {s["Conv Rate"]} conversion ({s["vs Pilot"]})')

            for note in sess_notes:
                st.caption(note)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 5. INPUT METHODS
# ══════════════════════════════════════════════════════════════════════════════

input_data = pi_data.get("input", pd.DataFrame())

if not input_data.empty and len(input_data) > 1:
    st.markdown("### 🖼 Input Methods")

    inp_rows = []
    for i in range(1, len(input_data)):
        row = input_data.iloc[i]
        method = str(row.iloc[0]).strip()
        if not method or method == "nan":
            continue
        inp_rows.append({
            "Method": method,
            "Users": safe_int(row.iloc[1]) if len(row) > 1 else 0,
            "Converters": safe_int(row.iloc[2]) if len(row) > 2 else 0,
            "Conv Rate": str(row.iloc[3]).strip() if len(row) > 3 else "",
            "vs Pilot": str(row.iloc[4]).strip() if len(row) > 4 else "",
            "Note": str(row.iloc[5]).strip() if len(row) > 5 else "",
        })

    if inp_rows:
        # Clean nan
        for r in inp_rows:
            for k in r:
                if str(r[k]) == "nan":
                    r[k] = ""

        inp_cols = st.columns(len(inp_rows))
        colors = {"Image / Photo": "#4F46E5", "Audio": "#F59E0B", "Text Only": "#10B981"}
        for col, r in zip(inp_cols, inp_rows):
            with col:
                c = colors.get(r["Method"], "#7C3AED")
                st.markdown(
                    f'<div style="text-align:center; padding:15px; background:#1E1E2E; '
                    f'border-radius:8px; border-top:3px solid {c};">'
                    f'<div style="font-size:0.85rem; color:#9CA3AF;">{r["Method"]}</div>'
                    f'<div style="font-size:2rem; font-weight:700; color:{c};">{r["Conv Rate"]}</div>'
                    f'<div style="font-size:0.8rem; color:#E5E7EB;">{r["Users"]} users → {r["Converters"]} converters</div>'
                    f'<div style="font-size:0.7rem; color:#9CA3AF; margin-top:4px;">{r["vs Pilot"]}</div>'
                    f'<div style="font-size:0.65rem; color:#6B7280; margin-top:2px;">{r["Note"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 6. TOP PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════

products = pi_data.get("products", pd.DataFrame())

if not products.empty and len(products) > 1:
    st.markdown("### 🌿 Top Products")

    prod_data = []
    for i in range(1, len(products)):
        row = products.iloc[i]
        name = str(row.iloc[0]).strip()
        if not name or name == "nan":
            continue
        prod_data.append({
            "Product": name,
            "Mentions": safe_int(row.iloc[1]) if len(row) > 1 else 0,
            "Unique Users": safe_int(row.iloc[2]) if len(row) > 2 else 0,
            "vs Pilot": str(row.iloc[3]).strip() if len(row) > 3 else "",
        })

    if prod_data:
        for r in prod_data:
            if str(r["vs Pilot"]) == "nan":
                r["vs Pilot"] = ""

        p_df = pd.DataFrame(prod_data)

        fig_p = go.Figure(go.Bar(
            y=p_df["Product"], x=p_df["Mentions"], orientation="h",
            text=p_df["Mentions"], textposition="outside",
            marker_color="#10B981",
        ))
        fig_p.update_layout(
            height=max(250, len(p_df) * 30), template="plotly_dark",
            margin=dict(l=10, r=80, t=10, b=10),
            yaxis=dict(autorange="reversed"),
            xaxis_title="Total Mentions",
        )
        st.plotly_chart(fig_p, use_container_width=True)

        st.dataframe(p_df, use_container_width=True, hide_index=True)

    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 7. ORDER DISTRIBUTION
# ══════════════════════════════════════════════════════════════════════════════

orders = pi_data.get("orders", pd.DataFrame())

if not orders.empty and len(orders) > 1:
    st.markdown("### 📦 Order Distribution")
    st.caption("How many orders each converting user placed")

    ord_data = []
    for i in range(1, len(orders)):
        row = orders.iloc[i]
        n_orders = str(row.iloc[0]).strip()
        if not n_orders or n_orders == "nan":
            continue
        ord_data.append({
            "Orders": n_orders,
            "Users": safe_int(row.iloc[1]) if len(row) > 1 else 0,
            "% of Converters": str(row.iloc[2]).strip() if len(row) > 2 else "",
            "Cumul %": str(row.iloc[4]).strip() if len(row) > 4 else "",
        })

    if ord_data:
        for r in ord_data:
            for k in r:
                if str(r[k]) == "nan":
                    r[k] = ""

        o_df = pd.DataFrame(ord_data)

        fig_o = go.Figure(go.Bar(
            x=[r["Orders"] for r in ord_data],
            y=[r["Users"] for r in ord_data],
            text=[r["Users"] for r in ord_data],
            textposition="outside",
            marker_color="#3B82F6",
        ))
        fig_o.update_layout(
            height=280, template="plotly_dark",
            margin=dict(l=20, r=20, t=10, b=20),
            xaxis_title="Orders placed", yaxis_title="Users",
        )
        st.plotly_chart(fig_o, use_container_width=True)

        # Key insights
        repeat = sum(r["Users"] for r in ord_data if r["Orders"] not in ("1", ""))
        total_conv = sum(r["Users"] for r in ord_data if r["Orders"] != "")
        single = next((r["Users"] for r in ord_data if r["Orders"] == "1"), 0)
        two_orders = next((r["Users"] for r in ord_data if r["Orders"] == "2"), 0)
        three_plus = sum(r["Users"] for r in ord_data if r["Orders"] not in ("1", "2", ""))

        if total_conv > 0:
            st.caption(f"**{repeat}** of {total_conv} converters ({repeat/total_conv*100:.0f}%) placed **2+ orders** — was 38% in pilot, now {repeat/total_conv*100:.0f}%")

        # Incentive threshold analysis (from deck)
        st.markdown("##### 💡 Incentive Threshold")
        it1, it2, it3 = st.columns(3)
        with it1:
            st.metric("3+ orders (organic)", three_plus, f"{three_plus/total_conv*100:.0f}% of converters" if total_conv else "")
        with it2:
            nudge_target = single + two_orders
            st.metric("1–2 orders (nudge target)", nudge_target, f"≥{nudge_target} incremental orders")
        with it3:
            st.metric("1 order only", single, f"{single/total_conv*100:.0f}% — was 62% in pilot" if total_conv else "")
        st.caption("Users at 1–2 orders are the incentive target. A nudge at order #3 (priority dispatch, loyalty credit) could unlock 100+ incremental orders from the existing base.")

    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 8. KEY ISSUES & ACTIONS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("### ⚠️ Key Issues & Actions")

issue_col1, issue_col2 = st.columns(2)

with issue_col1:
    st.markdown(
        '<div style="padding:15px; background:#1E1E2E; border-radius:8px; border-left:3px solid #EF4444;">'
        '<div style="font-size:0.75rem; color:#EF4444; font-weight:700;">P1 — BEFORE SCALE-UP</div>'
        '<div style="font-size:1rem; font-weight:700; color:#E5E7EB; margin-top:4px;">Backend Rejections: 78</div>'
        '<div style="font-size:0.8rem; color:#9CA3AF; margin-top:6px;">'
        'Sales area not configured: <b>57</b><br>'
        'EPOD not received: <b>20</b><br>'
        'Both are backend admin issues within PI\'s direct control. '
        'At 626 orders/82 days, unchecked rejections erode trust.'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("")
    st.markdown(
        '<div style="padding:15px; background:#1E1E2E; border-radius:8px; border-left:3px solid #EF4444;">'
        '<div style="font-size:0.75rem; color:#EF4444; font-weight:700;">P1 — BEFORE SCALE-UP</div>'
        '<div style="font-size:1rem; font-weight:700; color:#E5E7EB; margin-top:4px;">Registration Wall: 93 users blocked (24%)</div>'
        '<div style="font-size:0.8rem; color:#9CA3AF; margin-top:6px;">'
        'Down from 37% in pilot, but still significant. '
        'Pre-configure all expansion dealers before onboarding invites.'
        '</div></div>',
        unsafe_allow_html=True,
    )

with issue_col2:
    st.markdown(
        '<div style="padding:15px; background:#1E1E2E; border-radius:8px; border-left:3px solid #F59E0B;">'
        '<div style="font-size:0.75rem; color:#F59E0B; font-weight:700;">P2 — QUICK WIN</div>'
        '<div style="font-size:1rem; font-weight:700; color:#E5E7EB; margin-top:4px;">Bot Scope Gaps: 69 deflections</div>'
        '<div style="font-size:0.8rem; color:#9CA3AF; margin-top:6px;">'
        '15+ query types the bot should answer but refuses:<br>'
        '• Pricing queries (3×) — "Biovita kya rate h"<br>'
        '• Order history (2×) — "Purane order"<br>'
        '• Invoice status (3×) — post-order invoice queries<br>'
        '• Payment options (3×)<br>'
        '• Repeat order (1×) — "Dobara se si daliye"<br>'
        '• Stock availability (1×)<br>'
        '<b>No new integrations needed</b> — just config changes.'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("")
    st.markdown(
        '<div style="padding:15px; background:#1E1E2E; border-radius:8px; border-left:3px solid #F59E0B;">'
        '<div style="font-size:0.75rem; color:#F59E0B; font-weight:700;">P2 — QUICK WIN</div>'
        '<div style="font-size:1rem; font-weight:700; color:#E5E7EB; margin-top:4px;">Promote Image Ordering</div>'
        '<div style="font-size:0.8rem; color:#9CA3AF; margin-top:6px;">'
        'Image users convert at 78% vs 38% for text. '
        'Add photo prompt as primary CTA in welcome messages. '
        'Train TMs to coach dealers on sending shopping list photos.'
        '</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown(
    '<div style="padding:15px; background:#1E1E2E; border-radius:8px; border-left:3px solid #3B82F6;">'
    '<div style="font-size:0.75rem; color:#3B82F6; font-weight:700;">P3 — ROADMAP</div>'
    '<div style="font-size:0.8rem; color:#9CA3AF; margin-top:6px;">'
    '<b>Re-engagement nudges:</b> 55% of users never returned. Returning users convert at 72% vs 24% on first visit. '
    'A WhatsApp restock reminder is the lowest-effort way to unlock more repeat ordering. &nbsp;|&nbsp; '
    '<b>Inline cart in product responses:</b> Discovery users have 47% conv rate but 82% drop after info exchange. '
    'An "Add to Cart" prompt at peak intent closes the gap. &nbsp;|&nbsp; '
    '<b>Controlled cohort rollout:</b> Feb cohort had 53% conversion vs Jan\'s 36% — guided TM-led onboarding outperforms mass invites.'
    '</div></div>',
    unsafe_allow_html=True,
)
