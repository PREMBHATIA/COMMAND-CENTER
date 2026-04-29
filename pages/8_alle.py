"""All-e — Foundry Presales Pipeline & CRM."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="All-e Pipeline | Graas", page_icon="🤖", layout="wide")
st.markdown("## 🤖 All-e — Presales Pipeline & CRM")
st.markdown("[Open Source Sheet →](https://docs.google.com/spreadsheets/d/1lK9AJNA8-vVLPtkUWEq818DHnHWAsrCXgCq7vrvWLnI/edit)")

# ── Data Loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_alle_data():
    """Load All-e data — try Sheets API first, then CSV fallback."""
    try:
        from services.sheets_client import fetch_alle_active_presales
        df = fetch_alle_active_presales()
        if not df.empty:
            return df
    except Exception:
        pass
    # CSV fallback
    candidates = [
        "All-e - Foundry Presales Tracker - Active presales (1).csv",
        "All-e - Foundry Presales Tracker - Active presales.csv",
    ]
    for name in candidates:
        path = Path.home() / "Downloads" / name
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_meeting_summary():
    """Fetch the Revised - Summary of Meetings (28 Apr) tab."""
    try:
        from services.sheets_client import fetch_alle_meeting_summary
        df = fetch_alle_meeting_summary()
        if not df.empty:
            return df.values.tolist()
    except Exception:
        pass
    return []

raw = load_alle_data()
raw_mtg_summary = load_meeting_summary()

if raw.empty:
    st.warning("No All-e data found. Download the 'Active presales' tab from the All-e Foundry Presales Tracker sheet.")
    st.stop()

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ── Data Processing ───────────────────────────────────────────────────────────

df = raw.copy()

# Standardize column names
col_map = {}
for col in df.columns:
    cl = col.strip().lower()
    if 'lead name' in cl:
        col_map[col] = 'lead_name'
    elif 'vertical' in cl:
        col_map[col] = 'vertical'
    elif 'source' in cl:
        col_map[col] = 'source'
    elif 'agents of interest' in cl:
        col_map[col] = 'agents'
    elif 'lead status' in cl:
        col_map[col] = 'status'
    elif 'first conv' in cl:
        col_map[col] = 'first_conv'
    elif 'latest conv date' in cl:
        col_map[col] = 'latest_conv'
    elif 'latest conv detail' in cl:
        col_map[col] = 'conv_details'
    elif 'nda' in cl:
        col_map[col] = 'nda'
    elif 'poc required' in cl:
        col_map[col] = 'poc_required'
    elif 'poc scope' in cl:
        col_map[col] = 'poc_scope'
    elif 'poc eta' in cl:
        col_map[col] = 'poc_eta'
    elif col.strip().lower() == 'status':
        col_map[col] = 'deal_status'
    elif 'converted' in cl:
        col_map[col] = 'converted'
    elif 'comment' in cl:
        col_map[col] = 'comments'
    elif 'entity' in cl:
        col_map[col] = 'entity_type'
    elif 'email' in cl:
        col_map[col] = 'contacts'
    elif 'link' in cl and 'note' in cl:
        col_map[col] = 'notes_link'

df = df.rename(columns=col_map)

# Filter out empty rows
if 'lead_name' in df.columns:
    df = df[df['lead_name'].notna() & (df['lead_name'].str.strip() != '')].copy()
else:
    st.warning("Could not find 'Lead name' column in the data.")
    st.stop()

# Parse dates
for date_col in ['first_conv', 'latest_conv']:
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], format='mixed', errors='coerce')

# Calculate days since last contact
if 'latest_conv' in df.columns:
    today = pd.Timestamp.now()
    df['days_since_contact'] = (today - df['latest_conv']).dt.days
    # Use first_conv if latest is missing
    mask = df['days_since_contact'].isna() & df['first_conv'].notna()
    df.loc[mask, 'days_since_contact'] = (today - df.loc[mask, 'first_conv']).dt.days
else:
    df['days_since_contact'] = None

# Parse lead status for ordering
status_order = {'1-Pilot': 1, '2-POC': 2, '3-Proposal sent': 3, '4-TOF': 4}
if 'status' in df.columns:
    df['status_rank'] = df['status'].map(status_order).fillna(5)
else:
    df['status_rank'] = 5

# ══════════════════════════════════════════════════════════════════════════════

tab_gtm, tab_notes, tab_pipeline, tab_deals, tab_stale, tab_analytics = st.tabs([
    "🎯 GTM Tracker",
    "📝 Meeting Notes",
    "🔄 Pipeline",
    "📋 Active Deals",
    "⏰ Needs Follow-up",
    "📊 Analytics",
])


# ══════════════════════════════════════════════════════════════════════════════
# GTM DATA — 2026 Targets & Actuals
# ══════════════════════════════════════════════════════════════════════════════

gtm_target = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "T_New_Mtgs": [5, 10, 15, 18, 20, 20, 22, 22, 20, 18, 15, 10],
    "T_Cumul_Mtgs": [5, 15, 30, 48, 68, 88, 110, 132, 152, 170, 185, 195],
    "T_Free_POCs": [1, 3, 6, 10, 14, 18, 22, 26, 30, 34, 37, 39],
    "T_Pilots_Started": [0, 1, 2, 3, 5, 6, 7, 9, 10, 11, 12, 13],
    "T_Pilots_Finished": [0, 0, 0, 0, 1, 2, 4, 5, 7, 8, 10, 11],
    "T_Live_Customers": [0, 0, 0, 0, 0, 1, 2, 3, 5, 7, 9, 10],
    "T_Pilot_Revenue": [0, 15000, 30000, 45000, 75000, 90000, 105000, 135000, 150000, 165000, 180000, 195000],
    "T_Monthly_MRR": [0, 0, 0, 0, 0, 4000, 8000, 12000, 20000, 28000, 36000, 40000],
})

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
              7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

# ── Parse the "Revised - Summary of Meetings (28 Apr)" sheet ─────────────────
# Grid layout: India cols 0-8, SEA cols 10-18 (col 9 = blank separator)
# Section 1 (rows 1-8):  Source 1 (Greentern / Maddy)  → data starts row 3
# Section 2 (rows 10-17): Source 2 (Graas Network)      → data starts row 12
# Section 3 (rows 19-26): Overall with Actual / Target  → data starts row 21

_SHEET_MONTHS = ["Jan", "Feb", "Mar", "Apr"]  # only months in this tab

def _safe_int(val):
    try:
        s = str(val).strip()
        return int(float(s)) if s else 0
    except Exception:
        return 0

def _parse_source_section(grid, data_start_row, col_offset):
    """Parse a 6-row source section (count + companies per month)."""
    metric_keys = ["meetings", "positive", "others", "pocs", "pilots", "production"]
    result = {}
    for i, key in enumerate(metric_keys):
        row_idx = data_start_row + i
        if row_idx >= len(grid):
            break
        row = grid[row_idx]
        result[key] = {}
        for j, month in enumerate(_SHEET_MONTHS):
            cnt_col = col_offset + 1 + j * 2
            cos_col = col_offset + 2 + j * 2
            result[key][month] = {
                "count":     _safe_int(row[cnt_col]) if cnt_col < len(row) else 0,
                "companies": str(row[cos_col]).strip() if cos_col < len(row) else "",
            }
    return result

def _parse_overall_section(grid, data_start_row, col_offset):
    """Parse the 6-row overall section (actual + target per month)."""
    metric_keys = ["meetings", "positive", "others", "pocs", "pilots", "production"]
    result = {}
    for i, key in enumerate(metric_keys):
        row_idx = data_start_row + i
        if row_idx >= len(grid):
            break
        row = grid[row_idx]
        result[key] = {}
        for j, month in enumerate(_SHEET_MONTHS):
            act_col = col_offset + 1 + j * 2
            tgt_col = col_offset + 2 + j * 2
            result[key][month] = {
                "actual": _safe_int(row[act_col]) if act_col < len(row) else 0,
                "target": _safe_int(row[tgt_col]) if tgt_col < len(row) else 0,
            }
    return result

# Parse the sheet if available
msummary = {}
if raw_mtg_summary:
    grid = raw_mtg_summary
    msummary = {
        "india": {
            "greentern": _parse_source_section(grid, 3, 0),
            "graas":     _parse_source_section(grid, 12, 0),
            "overall":   _parse_overall_section(grid, 21, 0),
        },
        "sea": {
            "partner": _parse_source_section(grid, 3, 10),
            "graas":   _parse_source_section(grid, 12, 10),
            "overall": _parse_overall_section(grid, 21, 10),
        },
    }

# Build actuals arrays from the parsed summary (India + SEA combined)
actual_new_mtgs   = []
actual_cumul_mtgs = []
actual_pocs       = []
cumul = 0
for m in months:
    if msummary and m in _SHEET_MONTHS:
        ind = msummary["india"]["overall"]["meetings"].get(m, {}).get("actual", 0)
        sea = msummary["sea"]["overall"]["meetings"].get(m, {}).get("actual", 0)
        ind_poc = msummary["india"]["overall"]["pocs"].get(m, {}).get("actual", 0)
        sea_poc = msummary["sea"]["overall"]["pocs"].get(m, {}).get("actual", 0)
        n = ind + sea
        p = ind_poc + sea_poc
        cumul += n
        actual_new_mtgs.append(n)
        actual_cumul_mtgs.append(cumul)
        actual_pocs.append(p)
    else:
        actual_new_mtgs.append(None)
        actual_cumul_mtgs.append(None)
        actual_pocs.append(None)

# Proposals from Active presales sheet (status-based)
actual_proposals = []
for m in months:
    if m in _SHEET_MONTHS and 'first_conv' in df.columns:
        month_num = list(MONTH_ABBR.keys())[list(MONTH_ABBR.values()).index(m)]
        props = df[
            (df['first_conv'].dt.month == month_num) &
            (df['first_conv'].dt.year == 2026) &
            (df.get('status', pd.Series(dtype=str)).str.lower().str.contains('proposal', na=False))
        ]
        actual_proposals.append(len(props))
    else:
        actual_proposals.append(None)

gtm_target["A_New_Mtgs"]   = actual_new_mtgs
gtm_target["A_Cumul_Mtgs"] = actual_cumul_mtgs
gtm_target["A_Proposals"]  = actual_proposals
gtm_target["A_POCs"]       = actual_pocs


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0: GTM TRACKER
# ══════════════════════════════════════════════════════════════════════════════

with tab_gtm:
    st.markdown("### 2026 Execution & Revenue Roadmap")
    st.caption("Live data from [Revised - Summary of Meetings (28 Apr)](https://docs.google.com/spreadsheets/d/1lK9AJNA8-vVLPtkUWEq818DHnHWAsrCXgCq7vrvWLnI/edit?gid=1385475614#gid=1385475614) · India + SEA combined vs AOP targets")

    if not msummary:
        st.warning("Meeting summary sheet not loaded — showing targets only.")

    current_month_idx = datetime.now().month - 1  # 0-based (Apr = 3)

    # ── KPI Cards — YTD ───────────────────────────────────────────────────────
    ytd_target_mtgs = int(gtm_target.loc[current_month_idx, "T_Cumul_Mtgs"])
    ytd_actual_mtgs = int(gtm_target.loc[current_month_idx, "A_Cumul_Mtgs"] or 0)
    ytd_ach_mtgs    = f"{ytd_actual_mtgs/ytd_target_mtgs*100:.0f}%" if ytd_target_mtgs else "—"
    ytd_actual_pocs = int(sum(p for p in actual_pocs[:current_month_idx+1] if p is not None))
    ytd_target_pocs = int(gtm_target.loc[current_month_idx, "T_Free_POCs"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(f"Meetings YTD ({months[current_month_idx]})",
                  f"{ytd_actual_mtgs}", f"{ytd_ach_mtgs} of {ytd_target_mtgs} target")
    with c2:
        poc_ach = f"{ytd_actual_pocs/ytd_target_pocs*100:.0f}%" if ytd_target_pocs else "—"
        st.metric("POCs Completed (YTD)", ytd_actual_pocs, f"{poc_ach} of {ytd_target_pocs} target")
    with c3:
        st.metric("Pilots Started (Target)", gtm_target.loc[current_month_idx, "T_Pilots_Started"])
    with c4:
        st.metric("Pilot Revenue (Target)", f"${gtm_target.loc[current_month_idx, 'T_Pilot_Revenue']:,}")

    # ── Meetings: Target vs Actual (Jan → current month) ─────────────────────
    st.markdown("### 📊 New Meetings — Target vs Actual")

    _chart_months  = months[:current_month_idx + 1]
    _chart_targets = gtm_target["T_New_Mtgs"].iloc[:current_month_idx + 1].tolist()
    _chart_actuals = actual_new_mtgs[:current_month_idx + 1]

    fig_mtgs = go.Figure()
    fig_mtgs.add_trace(go.Bar(
        x=_chart_months, y=_chart_targets,
        name="Target", marker_color="#374151",
    ))
    actual_bars = [v if v is not None else 0 for v in _chart_actuals]
    bar_colors  = [
        "#10B981" if a >= t else "#EF4444"
        for a, t in zip(actual_bars, _chart_targets)
    ]
    fig_mtgs.add_trace(go.Bar(
        x=_chart_months, y=actual_bars,
        name="Actual", marker_color=bar_colors,
    ))
    fig_mtgs.update_layout(
        barmode="group", height=320, template="plotly_dark",
        margin=dict(l=20, r=20, t=10, b=20),
    )
    st.plotly_chart(fig_mtgs, use_container_width=True)

    # ── Cumulative Meetings ───────────────────────────────────────────────────
    st.markdown("### 📈 Cumulative Meetings — Target vs Actual")
    fig_cumul = go.Figure()
    fig_cumul.add_trace(go.Scatter(
        x=_chart_months, y=gtm_target["T_Cumul_Mtgs"].iloc[:current_month_idx+1].tolist(),
        mode="lines+markers", name="Target",
        line=dict(color="#6B7280", dash="dash", width=2),
    ))
    actual_cumul_plot = [v for v in actual_cumul_mtgs[:current_month_idx+1] if v is not None]
    fig_cumul.add_trace(go.Scatter(
        x=_chart_months[:len(actual_cumul_plot)], y=actual_cumul_plot,
        mode="lines+markers", name="Actual",
        line=dict(color="#4F46E5", width=3), marker=dict(size=10),
    ))
    fig_cumul.update_layout(
        height=300, template="plotly_dark",
        margin=dict(l=20, r=20, t=10, b=20),
    )
    st.plotly_chart(fig_cumul, use_container_width=True)

    # ── India vs SEA Breakdown ────────────────────────────────────────────────
    if msummary:
        st.markdown("---")
        st.markdown("### 🌏 India vs SEA Breakdown")

        _done_months = [m for m in _SHEET_MONTHS if m in _chart_months]
        breakdown_rows = []
        for m in _done_months:
            ind_act = msummary["india"]["overall"]["meetings"].get(m, {}).get("actual", 0)
            ind_tgt = msummary["india"]["overall"]["meetings"].get(m, {}).get("target", 0)
            sea_act = msummary["sea"]["overall"]["meetings"].get(m, {}).get("actual", 0)
            sea_tgt = msummary["sea"]["overall"]["meetings"].get(m, {}).get("target", 0)
            ind_pos = msummary["india"]["overall"]["positive"].get(m, {}).get("actual", 0)
            sea_pos = msummary["sea"]["overall"]["positive"].get(m, {}).get("actual", 0)
            ind_poc = msummary["india"]["overall"]["pocs"].get(m, {}).get("actual", 0)
            sea_poc = msummary["sea"]["overall"]["pocs"].get(m, {}).get("actual", 0)
            breakdown_rows.append({
                "Month": m,
                "India Mtgs": ind_act,
                "India Target": ind_tgt,
                "India Positive": ind_pos,
                "India POCs": ind_poc,
                "SEA Mtgs": sea_act,
                "SEA Target": sea_tgt,
                "SEA Positive": sea_pos,
                "SEA POCs": sea_poc,
                "Total": ind_act + sea_act,
            })

        if breakdown_rows:
            bdf = pd.DataFrame(breakdown_rows)
            st.dataframe(bdf, use_container_width=True, hide_index=True)

            # Stacked bar: India vs SEA
            fig_geo = go.Figure()
            fig_geo.add_trace(go.Bar(
                x=bdf["Month"], y=bdf["India Mtgs"],
                name="India", marker_color="#4F46E5",
            ))
            fig_geo.add_trace(go.Bar(
                x=bdf["Month"], y=bdf["SEA Mtgs"],
                name="SEA", marker_color="#10B981",
            ))
            fig_geo.update_layout(
                barmode="stack", height=280, template="plotly_dark",
                margin=dict(l=20, r=20, t=10, b=20),
                title="Meetings by Region",
            )
            st.plotly_chart(fig_geo, use_container_width=True)

        # ── By Source (India) ─────────────────────────────────────────────────
        st.markdown("### 🤝 India — By Source")
        source_rows = []
        for m in _done_months:
            gt_cnt = msummary["india"]["greentern"]["meetings"].get(m, {}).get("count", 0)
            gt_cos = msummary["india"]["greentern"]["meetings"].get(m, {}).get("companies", "")
            gn_cnt = msummary["india"]["graas"]["meetings"].get(m, {}).get("count", 0)
            gn_cos = msummary["india"]["graas"]["meetings"].get(m, {}).get("companies", "")
            gt_poc = msummary["india"]["greentern"]["pocs"].get(m, {}).get("count", 0)
            gn_poc = msummary["india"]["graas"]["pocs"].get(m, {}).get("count", 0)
            source_rows.append({
                "Month": m,
                "Greentern Mtgs": gt_cnt,
                "Greentern Companies": gt_cos,
                "Graas Network Mtgs": gn_cnt,
                "Graas Network Companies": gn_cos,
                "Greentern POCs": gt_poc,
                "Graas POCs": gn_poc,
            })

        for row in source_rows:
            m = row["Month"]
            with st.expander(f"**{m}** — Greentern: {row['Greentern Mtgs']} meetings · Graas Network: {row['Graas Network Mtgs']} meetings"):
                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown(f"**🤝 Greentern** ({row['Greentern Mtgs']} meetings, {row['Greentern POCs']} POCs)")
                    if row["Greentern Companies"]:
                        for co in row["Greentern Companies"].split(","):
                            co = co.strip()
                            if co:
                                st.markdown(f"  - {co}")
                with col_r:
                    st.markdown(f"**🏢 Graas Network** ({row['Graas Network Mtgs']} meetings, {row['Graas POCs']} POCs)")
                    if row["Graas Network Companies"]:
                        for co in row["Graas Network Companies"].split(","):
                            co = co.strip()
                            if co:
                                st.markdown(f"  - {co}")

        # ── SEA Source Breakdown ──────────────────────────────────────────────
        st.markdown("### 🌏 SEA — By Source")
        sea_source_rows = []
        for m in _done_months:
            pt_cnt = msummary["sea"]["partner"]["meetings"].get(m, {}).get("count", 0)
            pt_cos = msummary["sea"]["partner"]["meetings"].get(m, {}).get("companies", "")
            gn_cnt = msummary["sea"]["graas"]["meetings"].get(m, {}).get("count", 0)
            gn_cos = msummary["sea"]["graas"]["meetings"].get(m, {}).get("companies", "")
            sea_source_rows.append({
                "Month": m,
                "Partner Mtgs": pt_cnt,
                "Partner Companies": pt_cos,
                "Graas Network Mtgs": gn_cnt,
                "Graas Network Companies": gn_cos,
            })

        for row in sea_source_rows:
            m = row["Month"]
            with st.expander(f"**{m}** — Partner (Maddy/Haku): {row['Partner Mtgs']} meetings · Graas Network: {row['Graas Network Mtgs']} meetings"):
                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown(f"**🤝 Partner** ({row['Partner Mtgs']} meetings)")
                    if row["Partner Companies"]:
                        for co in row["Partner Companies"].split(","):
                            co = co.strip()
                            if co:
                                st.markdown(f"  - {co}")
                with col_r:
                    st.markdown(f"**🏢 Graas Network** ({row['Graas Network Mtgs']} meetings)")
                    if row["Graas Network Companies"]:
                        for co in row["Graas Network Companies"].split(","):
                            co = co.strip()
                            if co:
                                st.markdown(f"  - {co}")

    # ── Full Roadmap Table ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Full Roadmap — Targets vs Actuals")
    roadmap_display = gtm_target.iloc[:current_month_idx + 2][[
        "Month", "T_New_Mtgs", "T_Cumul_Mtgs", "T_Free_POCs",
        "T_Pilots_Started", "T_Pilots_Finished", "T_Live_Customers",
        "T_Pilot_Revenue", "T_Monthly_MRR",
        "A_New_Mtgs", "A_Cumul_Mtgs", "A_POCs",
    ]].copy()
    roadmap_display["T_Pilot_Revenue"] = roadmap_display["T_Pilot_Revenue"].apply(lambda x: f"${x:,}")
    roadmap_display["T_Monthly_MRR"]   = roadmap_display["T_Monthly_MRR"].apply(lambda x: f"${x:,}")
    roadmap_display = roadmap_display.rename(columns={
        "T_New_Mtgs": "Target Mtgs", "T_Cumul_Mtgs": "Target Cumul",
        "T_Free_POCs": "Target POCs", "T_Pilots_Started": "Target Pilots",
        "T_Pilots_Finished": "Pilots Done", "T_Live_Customers": "Live Cust",
        "T_Pilot_Revenue": "Pilot Rev", "T_Monthly_MRR": "MRR",
        "A_New_Mtgs": "Actual Mtgs", "A_Cumul_Mtgs": "Actual Cumul",
        "A_POCs": "Actual POCs",
    })
    st.dataframe(roadmap_display, use_container_width=True, hide_index=True)
    st.caption("Assumption: 13 Paid Pilots → 10 Customers in Production = $195K + $148K = **$343K invoiced revenue in 2026**")



# ══════════════════════════════════════════════════════════════════════════════
# TAB: MEETING NOTES  (pulled from Slack channels via Granola shares)
# ══════════════════════════════════════════════════════════════════════════════


with tab_notes:
    st.markdown("### 📝 Latest Meeting Notes")
    st.caption("Auto-pulled from Slack — `#ebu-offerings-gtm` (India) and `#my-gtm-alle` (MY/SEA)")

    # ── Build notes from sheet's notes_link column ────────────────────────────
    st.markdown("#### 🔗 Notes by Lead (from Presales Tracker)")

    if 'notes_link' in df.columns:
        leads_with_notes = df[df['notes_link'].notna() & (df['notes_link'].str.strip() != '')].copy()
        if not leads_with_notes.empty:
            leads_with_notes = leads_with_notes.sort_values('latest_conv', ascending=False, na_position='last')
            for _, row in leads_with_notes.iterrows():
                lead = row['lead_name']
                raw_links = str(row['notes_link']).strip()
                status = row.get('status', '')
                last_contact = row['latest_conv'].strftime('%d %b') if pd.notna(row.get('latest_conv')) else '—'
                vertical = row.get('vertical', '')

                # Parse links
                link_parts = re.findall(r'https?://[^\s]+', raw_links)
                granola_count = sum(1 for l in link_parts if 'granola.ai' in l)
                gdoc_count = sum(1 for l in link_parts if 'docs.google.com' in l)

                # Icon based on status
                status_icon = {"1-Pilot": "🟢", "2-POC": "🔵", "3-Proposal sent": "🟡", "4-TOF": "⚪"}.get(status, "⚫")

                with st.expander(f"{status_icon} **{lead}** — {vertical} — last contact {last_contact} — {len(link_parts)} note(s)"):
                    # Show all links
                    for i, link in enumerate(link_parts, 1):
                        if 'granola.ai' in link:
                            st.markdown(f"📋 [Granola Note {i}]({link})")
                        elif 'docs.google.com' in link:
                            st.markdown(f"📄 [Google Doc {i}]({link})")
                        else:
                            st.markdown(f"🔗 [Link {i}]({link})")

                    # Show conversation details if available
                    if pd.notna(row.get('conv_details')) and str(row['conv_details']).strip():
                        st.markdown("**Latest conversation:**")
                        st.markdown(str(row['conv_details'])[:500])
        else:
            st.info("No leads with notes links found.")
    else:
        st.info("Notes link column not found in sheet.")

    st.markdown("---")

    # ── Recent Slack recaps ───────────────────────────────────────────────────
    st.markdown("#### 💬 Recent Meeting Recaps (from Slack)")
    st.caption("Key takeaways shared in `#ebu-offerings-gtm` and `#my-gtm-alle`")

    # Try live Slack pull; fall back to cached snapshot
    @st.cache_data(ttl=1800)
    def _fetch_slack_notes():
        try:
            from services.slack_notes import fetch_meeting_notes
            notes = fetch_meeting_notes(lookback_days=30)
            if notes:
                return notes, True
        except Exception:
            pass
        return None, False

    slack_recaps, is_live = _fetch_slack_notes()

    if st.button("🔄 Refresh Slack Notes", key="refresh_slack_notes"):
        _fetch_slack_notes.clear()
        st.rerun()

    # Fallback: hardcoded snapshot (last pulled 13 Apr 2026)
    if not slack_recaps:
        is_live = False
        slack_recaps = [
            {
                "client": "Orient Bell",
                "date": "10 Apr",
                "channel": "#ebu-offerings-gtm",
                "author": "Gaurav Girotra",
                "granola": "https://notes.granola.ai/t/374658c2-7836-4553-b1d0-89337a86612f-008umkv4",
                "takeaways": [
                    "POC kicked off for floor tiles as a category",
                    "To be delivered by end of next week (assuming catalogue & details received)",
                    "GG to set up f2f meeting for POC walkthrough and Pilot next steps",
                ],
            },
            {
                "client": "Unicharm",
                "date": "10 Apr",
                "channel": "#ebu-offerings-gtm",
                "author": "Ashwin Puri",
                "granola": "https://notes.granola.ai/t/b8d38fbc-26bb-4f6d-9f97-510409956be5-00best9l",
                "takeaways": [
                    "Existing MP customer expanding markets — SGD $45M MYR/month MY business",
                    "Enablement: extend SG DKSH model to MY for Lazada/Shopee",
                    "Hoppr: provide Deanna access for SG regional data team",
                    "All-e: discovery call to be set up in KL with IT team (Ashwin to arrange)",
                    "Offline AI agent for 126 merchandising + 170 sales team — $10M USD/month MY business",
                ],
            },
            {
                "client": "RSPL Group",
                "date": "9 Apr",
                "channel": "#ebu-offerings-gtm",
                "author": "Gaurav Girotra",
                "granola": "https://notes.granola.ai/t/5b967b55-5142-452f-a0bc-0a5381f85906-008umkv4",
                "takeaways": [
                    "Sales use case not a need — dealer ordering is not an issue for them",
                    "Possible use case: factory OCR (30 factories) for handwritten/typed info routing",
                    "They will come back after discussing internally",
                ],
            },
            {
                "client": "Tata 1mg",
                "date": "9 Apr",
                "channel": "#ebu-offerings-gtm",
                "author": "Gaurav Girotra",
                "granola": "https://notes.granola.ai/t/1fe5a8ad-e368-4995-b0d7-d56c93d82130-008umkv4",
                "takeaways": [
                    "Prem to work with Nikhil on closing out commercials",
                    "Amruta to test accuracy improvements with new cleanly labelled prescriptions",
                ],
            },
            {
                "client": "Dalmia Cement",
                "date": "8 Apr",
                "channel": "#ebu-offerings-gtm",
                "author": "Gaurav Girotra",
                "granola": "https://notes.granola.ai/t/2beb83b8-b2eb-49f5-9702-f8712d8ef5e0-008umkv4",
                "takeaways": [
                    "Very low SKUs (5 active), weekly ordering, 50K dealers — no opportunity",
                    "They already have an AI agent deployed for dealer ordering",
                    "Cement may not be a good fit — low SKU density, infrequent orders",
                ],
            },
            {
                "client": "Sunway",
                "date": "6 Apr",
                "channel": "#my-gtm-alle",
                "author": "Sahil Tyagi",
                "granola": "https://notes.granola.ai/t/d82cf004-9cd3-4fc1-b707-86a56c96e897-009c2hma",
                "takeaways": [],
            },
            {
                "client": "Decathlon",
                "date": "2 Apr",
                "channel": "#my-gtm-alle",
                "author": "Prem Bhatia",
                "granola": "https://notes.granola.ai/t/e88082b9-a0b4-44f9-9646-d56f7c353a5c-008umkv4",
                "takeaways": [],
            },
            {
                "client": "Beacon Mart",
                "date": "1 Apr",
                "channel": "#my-gtm-alle",
                "author": "Sahil Tyagi",
                "granola": "https://notes.granola.ai/t/813537a7-c353-4cf1-bca5-cf165966e9a4-008umkv4",
                "takeaways": [
                    "Cindy to send Thomas Hoppr login for e-commerce team (5 users)",
                    "Send Thomas videos on offline agent (Ollie) for IT team",
                    "Follow up with proposal for f2f meeting in KL once IT is looped in",
                    "Thomas to share Graas videos with Beacon Mart IT team",
                ],
            },
        ]

    if is_live:
        missing_count = sum(1 for r in slack_recaps if r.get("missing_granola"))
        status_msg = f"🔴 Live — {len(slack_recaps)} meeting note(s) from Slack (last 30 days)"
        if missing_count:
            status_msg += f" — **{missing_count} missing Granola notes**"
        st.success(status_msg)
    else:
        st.info("📸 Showing cached snapshot — add `SLACK_BOT_TOKEN` to `.env` to enable live refresh")

    # Show meetings missing Granola notes first as a warning block
    missing_granola = [r for r in slack_recaps if r.get("missing_granola")]
    if missing_granola:
        st.warning(f"⚠️ **{len(missing_granola)} meeting(s) without Granola notes** — follow up to get notes recorded")
        for recap in missing_granola:
            st.markdown(f"- **{recap['client']}** — {recap['date']} — {recap['author']} ({recap['channel']})")
        st.markdown("---")

    for recap in slack_recaps:
        takeaway_count = len(recap["takeaways"])
        if recap.get("missing_granola"):
            icon = "⚠️"
            flag = " — **NO GRANOLA NOTES**"
        else:
            icon = "📋"
            flag = ""
        label = f"{icon} **{recap['client']}** — {recap['date']} — {recap['author']} — {recap['channel']}"
        if takeaway_count:
            label += f" — {takeaway_count} action(s)"
        label += flag

        with st.expander(label):
            if recap.get("missing_granola"):
                st.error("No Granola notes shared for this meeting. Please follow up with the attendee.")
            if recap.get("summary"):
                st.markdown(recap["summary"])
                st.markdown("---")
            if recap["takeaways"]:
                for t in recap["takeaways"]:
                    st.markdown(f"- {t}")
            elif not recap.get("missing_granola"):
                st.caption("Granola notes shared — open link for details")
            if recap.get("granola"):
                st.markdown(f"[Open full Granola notes]({recap['granola']})")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

with tab_pipeline:

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    total = len(df)
    pilots = len(df[df['status'] == '1-Pilot']) if 'status' in df.columns else 0
    pocs = len(df[df['status'] == '2-POC']) if 'status' in df.columns else 0
    proposals = len(df[df['status'] == '3-Proposal sent']) if 'status' in df.columns else 0
    tof = len(df[df['status'] == '4-TOF']) if 'status' in df.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total Leads", total)
    with c2:
        st.metric("Pilots", pilots)
    with c3:
        st.metric("POC", pocs)
    with c4:
        st.metric("Proposals Sent", proposals)
    with c5:
        st.metric("Top of Funnel", tof)

    # ── Month View — Actual vs Target (only through current month) ────────────
    st.markdown("### Monthly Progress vs Target")

    _current_month_idx = datetime.now().month - 1  # 0-based (Jan=0, Apr=3)
    _show_months = months[:_current_month_idx + 1]  # Jan through current month

    month_rows = []
    for m in _show_months:
        idx = months.index(m)
        t_mtgs = gtm_target.loc[idx, "T_New_Mtgs"]
        t_cumul = gtm_target.loc[idx, "T_Cumul_Mtgs"]
        t_pocs = gtm_target.loc[idx, "T_Free_POCs"]
        t_pilots = gtm_target.loc[idx, "T_Pilots_Started"]

        a_mtgs = actual_new_mtgs[idx]
        a_cumul = actual_cumul_mtgs[idx]
        a_props = actual_proposals[idx]

        if a_mtgs is not None:
            mtg_status = "✅" if a_mtgs >= t_mtgs else "⚠️"
            month_rows.append({
                "Month": m,
                "Mtgs (A/T)": f"{mtg_status} {a_mtgs} / {t_mtgs}",
                "Cumul (A/T)": f"{a_cumul} / {t_cumul}",
                "Proposals": a_props,
                "Target POCs": t_pocs,
                "Target Pilots": t_pilots,
            })
        else:
            month_rows.append({
                "Month": m,
                "Mtgs (A/T)": f"— / {t_mtgs}",
                "Cumul (A/T)": f"— / {t_cumul}",
                "Proposals": "—",
                "Target POCs": t_pocs,
                "Target Pilots": t_pilots,
            })

    st.dataframe(pd.DataFrame(month_rows), use_container_width=True, hide_index=True)

    # ── Deals by stage ────────────────────────────────────────────────────────
    st.markdown("### Deals by Stage")
    if 'status' in df.columns:
        for status_label, color, icon in [
            ("1-Pilot", "#10B981", "🟢"),
            ("2-POC", "#06B6D4", "🔵"),
            ("3-Proposal sent", "#F59E0B", "🟡"),
        ]:
            stage_deals = df[df['status'] == status_label].sort_values('days_since_contact', na_position='last')
            if not stage_deals.empty:
                st.markdown(f"#### {icon} {status_label} ({len(stage_deals)} deals)")
                for _, deal in stage_deals.iterrows():
                    days = f"{int(deal['days_since_contact'])}d ago" if pd.notna(deal['days_since_contact']) else "—"
                    vertical = deal.get('vertical', '')
                    source = deal.get('source', '')
                    st.markdown(f"- **{deal['lead_name']}** ({vertical}) — {source} — last contact {days}")

    # ── Funnel Chart (below) ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Sales Funnel")

    funnel_stages = ["4 - Top of Funnel", "3 - Proposal Sent", "2 - POC", "1 - Pilot"]
    funnel_values = [tof, proposals, pocs, pilots]

    fig_funnel = go.Figure(go.Funnel(
        y=funnel_stages,
        x=funnel_values,
        textinfo="value+text",
        marker=dict(color=["#6B7280", "#F59E0B", "#06B6D4", "#10B981"]),
        connector=dict(line=dict(color="#374151", width=2)),
    ))
    fig_funnel.update_layout(height=350, template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_funnel, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: ACTIVE DEALS
# ══════════════════════════════════════════════════════════════════════════════

with tab_deals:
    st.markdown("### All Active Deals")

    # Filters
    col_status, col_vertical, col_source, col_search = st.columns(4)

    with col_status:
        statuses = sorted(df['status'].dropna().unique().tolist()) if 'status' in df.columns else []
        sel_status = st.multiselect("Status", statuses, default=statuses, key="alle_status")
    with col_vertical:
        verticals = sorted(df['vertical'].dropna().unique().tolist()) if 'vertical' in df.columns else []
        sel_verticals = st.multiselect("Vertical", verticals, default=verticals, key="alle_vert")
    with col_source:
        sources = sorted(df['source'].dropna().unique().tolist()) if 'source' in df.columns else []
        sel_sources = st.multiselect("Source", sources, default=sources, key="alle_src")
    with col_search:
        search = st.text_input("Search lead", "", key="alle_search")

    filtered = df.copy()
    if 'status' in filtered.columns:
        filtered = filtered[filtered['status'].isin(sel_status)]
    if 'vertical' in filtered.columns:
        filtered = filtered[filtered['vertical'].isin(sel_verticals)]
    if 'source' in filtered.columns:
        filtered = filtered[filtered['source'].isin(sel_sources)]
    if search:
        filtered = filtered[filtered['lead_name'].str.contains(search, case=False, na=False)]

    filtered = filtered.sort_values('status_rank')

    # Build display table
    display_cols = ['lead_name', 'vertical', 'source', 'agents', 'status', 'first_conv', 'latest_conv']
    available_cols = [c for c in display_cols if c in filtered.columns]

    display = filtered[available_cols].copy()

    # Add row numbers
    display = display.reset_index(drop=True)
    display.insert(0, '#', range(1, len(display) + 1))

    # Format dates
    for dc in ['first_conv', 'latest_conv']:
        if dc in display.columns:
            display[dc] = display[dc].dt.strftime('%d %b %Y').fillna('—')

    rename_map = {
        'lead_name': 'Lead', 'vertical': 'Vertical', 'source': 'Source',
        'agents': 'Product Interest', 'status': 'Status',
        'first_conv': 'First Contact', 'latest_conv': 'Last Contact',
    }
    display = display.rename(columns={k: v for k, v in rename_map.items() if k in display.columns})

    def status_color(val):
        colors = {
            '1-Pilot': 'background-color: #065F46; color: white',
            '2-POC': 'background-color: #1E40AF; color: white',
            '3-Proposal sent': 'background-color: #92400E; color: white',
            '4-TOF': 'background-color: #374151; color: white',
        }
        return colors.get(val, '')

    def days_color(val):
        try:
            v = float(val)
            if v > 21:
                return 'background-color: #7F1D1D; color: white'
            elif v > 14:
                return 'background-color: #92400E; color: white'
            return ''
        except:
            return ''

    style = display.style
    if 'Status' in display.columns:
        style = style.map(status_color, subset=['Status'])
    if 'Days Silent' in display.columns:
        style = style.map(days_color, subset=['Days Silent'])

    st.dataframe(style, use_container_width=True, height=600, hide_index=True)

    # ── Deal Detail ───────────────────────────────────────────────────────────
    st.markdown("### Deal Detail")
    deal_names = filtered['lead_name'].tolist()
    selected_deal = st.selectbox("Select lead", deal_names, key="alle_detail")

    if selected_deal:
        deal = df[df['lead_name'] == selected_deal].iloc[0]

        col_info, col_meta = st.columns([3, 2])
        with col_info:
            st.markdown(f"**{deal['lead_name']}** — {deal.get('vertical', '')} ({deal.get('entity_type', '')})")
            st.markdown(f"Status: **{deal.get('status', '')}** | Source: **{deal.get('source', '')}**")
            st.markdown(f"Product Interest: **{deal.get('agents', '')}**")
            if pd.notna(deal.get('contacts')):
                st.markdown(f"Contacts: {deal['contacts']}")
        with col_meta:
            if pd.notna(deal.get('first_conv')):
                st.markdown(f"First Contact: **{deal['first_conv'].strftime('%d %b %Y') if pd.notna(deal.get('first_conv')) else '—'}**")
            if pd.notna(deal.get('latest_conv')):
                st.markdown(f"Last Contact: **{deal['latest_conv'].strftime('%d %b %Y') if pd.notna(deal.get('latest_conv')) else '—'}**")
            if pd.notna(deal.get('days_since_contact')):
                st.markdown(f"Days Since Contact: **{int(deal['days_since_contact'])}**")

        if pd.notna(deal.get('conv_details')) and str(deal['conv_details']).strip():
            with st.expander("📝 Latest Conversation Details"):
                st.markdown(str(deal['conv_details'])[:2000])

        if pd.notna(deal.get('comments')) and str(deal['comments']).strip():
            with st.expander("💬 Comments"):
                st.markdown(str(deal['comments'])[:2000])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: NEEDS FOLLOW-UP
# ══════════════════════════════════════════════════════════════════════════════

with tab_stale:

    # ── Proposals Needing Chasers ─────────────────────────────────────────────
    st.markdown("### 📨 Proposals Needing a Chaser")
    st.caption("Proposals sent 14+ days ago that may need a follow-up")

    if 'days_since_contact' in df.columns and 'status' in df.columns:
        proposals_sent = df[df['status'] == '3-Proposal sent'].copy()

        overdue = proposals_sent[proposals_sent['days_since_contact'] > 30].sort_values('days_since_contact', ascending=False)
        upcoming = proposals_sent[(proposals_sent['days_since_contact'] > 14) & (proposals_sent['days_since_contact'] <= 30)].sort_values('days_since_contact', ascending=False)

        if not overdue.empty:
            st.markdown(f"#### 🔴 Overdue — Proposal sent 30+ days ago ({len(overdue)})")
            for _, deal in overdue.iterrows():
                days = int(deal['days_since_contact'])
                source = deal.get('source', '')
                st.markdown(f"- **{deal['lead_name']}** — {days} days since last update — Owner: {source}")

        if not upcoming.empty:
            st.markdown(f"#### 🟡 Coming Due — Proposal sent 14-30 days ago ({len(upcoming)})")
            for _, deal in upcoming.iterrows():
                days = int(deal['days_since_contact'])
                source = deal.get('source', '')
                st.markdown(f"- **{deal['lead_name']}** — {days} days since last update — Owner: {source}")

        if overdue.empty and upcoming.empty:
            st.success("All proposals are fresh — no chasers needed right now.")

    # ── POC / Pilot Check-ins ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔄 POC & Pilot Check-ins")
    st.caption("Active POCs and Pilots — are they progressing?")

    if 'days_since_contact' in df.columns and 'status' in df.columns:
        active = df[df['status'].isin(['1-Pilot', '2-POC'])].sort_values('days_since_contact', ascending=False).copy()

        if not active.empty:
            for _, deal in active.iterrows():
                days = int(deal['days_since_contact']) if pd.notna(deal['days_since_contact']) else 0
                source = deal.get('source', '')
                icon = "🟢" if days < 14 else "🟡" if days < 30 else "🔴"
                st.markdown(f"- {icon} **{deal['lead_name']}** ({deal['status']}) — last update {days}d ago — Owner: {source}")
        else:
            st.info("No active POCs or Pilots.")

    else:
        st.info("No date data available.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

with tab_analytics:
    st.markdown("### Pipeline Analytics")

    col_left, col_right = st.columns(2)

    # By Vertical
    with col_left:
        st.markdown("#### By Vertical")
        if 'vertical' in df.columns:
            vert_counts = df['vertical'].value_counts().reset_index()
            vert_counts.columns = ['Vertical', 'Count']
            fig_vert = px.bar(vert_counts.sort_values('Count', ascending=True),
                              x='Count', y='Vertical', orientation='h',
                              color_discrete_sequence=['#4F46E5'])
            fig_vert.update_layout(height=350, template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_vert, use_container_width=True)

    # By Source
    with col_right:
        st.markdown("#### By Lead Source")
        if 'source' in df.columns:
            source_counts = df['source'].value_counts().reset_index()
            source_counts.columns = ['Source', 'Count']
            fig_src = px.pie(source_counts, names='Source', values='Count',
                             color_discrete_sequence=px.colors.qualitative.Set2)
            fig_src.update_layout(height=350, template="plotly_dark")
            st.plotly_chart(fig_src, use_container_width=True)

    # By Status × Vertical heatmap
    st.markdown("#### Pipeline Heatmap — Status x Vertical")
    if 'status' in df.columns and 'vertical' in df.columns:
        cross = pd.crosstab(df['vertical'], df['status'])
        fig_heat = px.imshow(
            cross, text_auto=True,
            color_continuous_scale=['#1a1a2e', '#4F46E5', '#10B981'],
            labels=dict(x="Stage", y="Vertical", color="Count"),
        )
        fig_heat.update_layout(height=400, template="plotly_dark")
        st.plotly_chart(fig_heat, use_container_width=True)

    # Timeline — deals by first contact month
    st.markdown("#### Pipeline Growth — Deals by First Contact Month")
    if 'first_conv' in df.columns:
        timeline = df[df['first_conv'].notna()].copy()
        timeline['month'] = timeline['first_conv'].dt.to_period('M').astype(str)
        monthly = timeline.groupby('month').size().reset_index(name='New Leads')
        fig_time = px.bar(monthly, x='month', y='New Leads', color_discrete_sequence=['#7C3AED'])
        fig_time.update_layout(height=300, template="plotly_dark", xaxis_title="Month", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_time, use_container_width=True)
