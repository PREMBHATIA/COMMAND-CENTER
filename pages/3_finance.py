"""Finance Dashboard — P&L, GP & Revenue."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Finance | Graas", page_icon="💰", layout="wide")
st.markdown("## 💰 Finance")

# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_money(s):
    """Parse money values including negatives in parentheses like (245,618)."""
    s = str(s).replace("$", "").replace('"', "").strip()
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = re.sub(r'[^\d.\-]', '', s)
    try:
        val = float(s)
        return -val if negative else val
    except:
        return 0.0

def format_money(val):
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    elif abs(val) >= 1_000:
        return f"${val/1_000:.0f}K"
    return f"${val:,.0f}"

def format_money_short(val):
    """Shorter format for tables."""
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.2f}M"
    elif abs(val) >= 1_000:
        return f"${val/1_000:.1f}K"
    return f"${val:,.0f}"

# ── Data Loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_pnl_from_excel(file_bytes: bytes) -> pd.DataFrame:
    """Parse Summary tab from uploaded Excel bytes."""
    import io
    xl = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    # Try common tab names
    for name in xl.sheet_names:
        if "summary" in name.lower():
            return xl.parse(name, header=None)
    # Fall back to first sheet
    return xl.parse(xl.sheet_names[0], header=None)

def load_pnl_data(file_bytes=None):
    """Load P&L Summary — uploaded Excel first, then local CSV fallback."""
    if file_bytes is not None:
        return load_pnl_from_excel(file_bytes)
    # Local CSV fallback (works when running locally)
    csv_path = Path.home() / "Downloads" / "Graas FY 2026 Actuals.xlsx - Summary.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, header=None)
    return pd.DataFrame()

# ── File upload ───────────────────────────────────────────────────────────────
col_btn, col_up = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
with col_up:
    uploaded = st.file_uploader(
        "Upload **Graas FY 2026 Actuals.xlsx**",
        type=["xlsx"],
        label_visibility="collapsed",
        key="finance_upload",
    )

file_bytes = uploaded.read() if uploaded else None
raw_pnl = load_pnl_data(file_bytes)

# ── Parse P&L Summary ───────────────────────────────────────────────────────
# Structure: 3 column blocks — Actuals (3-21), AOP (23-41), Variance (43-61)
# Row layout: GMV (3-17), Gross Rev (19-31), Net Rev (33-47), CoS (49-61),
#             Gross Profit (63-75), GP% (77-81), OpEx (85-115), EBITDA (117)
# BUs: Total, ABU, Marketplace, EBU, Platform
# Each BU has: Total, -New, -Existing

pnl = {}
MONTHS = ["Jan", "Feb", "Mar"]
MONTH_COLS_ACT = {0: 3, 1: 4, 2: 5}  # Actuals month columns
Q1_COL_ACT = 6
MONTH_COLS_AOP = {0: 23, 1: 24, 2: 25}  # AOP month columns
Q1_COL_AOP = 26
MONTH_COLS_VAR = {0: 43, 1: 44, 2: 45}  # Variance month columns
Q1_COL_VAR = 46

# Key rows in the CSV
PNL_ROWS = {
    # (metric, bu) -> row index
    ("GMV", "Total"): 3, ("GMV", "ABU"): 4, ("GMV", "Marketplace"): 7,
    ("GMV", "EBU"): 10, ("GMV", "Platform"): 13,
    ("Gross Rev", "Total"): 19, ("Gross Rev", "ABU"): 20, ("Gross Rev", "Marketplace"): 23,
    ("Gross Rev", "EBU"): 26, ("Gross Rev", "Platform"): 29,
    ("Net Rev", "Total"): 33, ("Net Rev", "ABU"): 34, ("Net Rev", "Marketplace"): 37,
    ("Net Rev", "EBU"): 40, ("Net Rev", "Platform"): 43,
    ("CoS", "Total"): 49, ("CoS", "ABU"): 50, ("CoS", "Marketplace"): 53,
    ("CoS", "EBU"): 56, ("CoS", "Platform"): 59,
    ("GP", "Total"): 63, ("GP", "ABU"): 64, ("GP", "Marketplace"): 67,
    ("GP", "EBU"): 70, ("GP", "Platform"): 73,
    ("GP%", "Total"): 77, ("GP%", "ABU"): 78, ("GP%", "Marketplace"): 79,
    ("GP%", "EBU"): 80, ("GP%", "Platform"): 81,
    ("OpEx", "Total"): 85,
    ("HC Fixed", "Total"): 87, ("HC Fixed", "S&M"): 88, ("HC Fixed", "Delivery"): 89,
    ("HC Fixed", "Tech"): 93, ("HC Fixed", "G&A"): 95,
    ("HC Variable", "Total"): 99,
    ("Other Exp", "Total"): 102,
    ("EBITDA", "Total"): 117,
}

if not raw_pnl.empty:
    for (metric, bu), row_idx in PNL_ROWS.items():
        if row_idx < len(raw_pnl):
            row = raw_pnl.iloc[row_idx]
            pnl[(metric, bu)] = {
                "actual": {m: parse_money(row.iloc[MONTH_COLS_ACT[i]]) for i, m in enumerate(MONTHS)},
                "actual_q1": parse_money(row.iloc[Q1_COL_ACT]),
                "aop": {m: parse_money(row.iloc[MONTH_COLS_AOP[i]]) for i, m in enumerate(MONTHS)},
                "aop_q1": parse_money(row.iloc[Q1_COL_AOP]),
                "variance": {m: parse_money(row.iloc[MONTH_COLS_VAR[i]]) for i, m in enumerate(MONTHS)},
                "variance_q1": parse_money(row.iloc[Q1_COL_VAR]),
            }

# ══════════════════════════════════════════════════════════════════════════════


_has_pnl = not raw_pnl.empty and bool(pnl)

if not _has_pnl:
    st.info("No P&L data — upload the Excel above to see P&L, or scroll down for Headcount & AR.")

# ── P&L Section (only if data available) ─────────────────────────────
if _has_pnl:
    st.markdown("### Graas P&L — FY 2026 Actuals vs AOP")
    st.caption("Source of truth from Finance | Updated monthly")

# ── Determine latest month with data ─────────────────────────────────
latest_month_idx = -1
for i, m in enumerate(MONTHS):
    if ("GP", "Total") in pnl and pnl[("GP", "Total")]["actual"].get(m, 0) != 0:
        latest_month_idx = i
latest_month = MONTHS[latest_month_idx] if latest_month_idx >= 0 else "Jan"

# ── Top-level KPIs ───────────────────────────────────────────────────
def get_val(metric, bu, field, month=None):
    key = (metric, bu)
    if key not in pnl:
        return 0
    if month:
        return pnl[key][field].get(month, 0)
    return pnl[key].get(f"{field}_q1", 0)

# YTD actuals (sum months with data)
ytd_months = MONTHS[:latest_month_idx + 1]

gp_ytd = sum(get_val("GP", "Total", "actual", m) for m in ytd_months)
gp_aop_ytd = sum(get_val("GP", "Total", "aop", m) for m in ytd_months)
rev_ytd = sum(get_val("Net Rev", "Total", "actual", m) for m in ytd_months)
rev_aop_ytd = sum(get_val("Net Rev", "Total", "aop", m) for m in ytd_months)
ebitda_ytd = sum(get_val("EBITDA", "Total", "actual", m) for m in ytd_months)
ebitda_aop_ytd = sum(get_val("EBITDA", "Total", "aop", m) for m in ytd_months)
opex_ytd = sum(get_val("OpEx", "Total", "actual", m) for m in ytd_months)
opex_aop_ytd = sum(get_val("OpEx", "Total", "aop", m) for m in ytd_months)

gp_var = gp_ytd - gp_aop_ytd
rev_var = rev_ytd - rev_aop_ytd
ebitda_var = ebitda_ytd - ebitda_aop_ytd

if _has_pnl:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Gross Profit (YTD)", format_money(gp_ytd),
                   f"{'+' if gp_var >= 0 else ''}{format_money(gp_var)} vs AOP")
    with c2:
        st.metric("Net Revenue (YTD)", format_money(rev_ytd),
                   f"{'+' if rev_var >= 0 else ''}{format_money(rev_var)} vs AOP")
    with c3:
        st.metric("EBITDA (YTD)", format_money(ebitda_ytd),
                   f"{'+' if ebitda_var >= 0 else ''}{format_money(ebitda_var)} vs AOP")
    with c4:
        gp_pct = (gp_ytd / rev_ytd * 100) if rev_ytd else 0
        st.metric("GP Margin", f"{gp_pct:.0f}%",
                   f"OpEx: {format_money(opex_ytd)}")

if _has_pnl:
    # ── Monthly P&L Table ────────────────────────────────────────────────
    st.markdown("### Monthly P&L — Actuals vs AOP")

    metrics_for_table = [
        ("GMV", "Total", "GMV"),
        ("Gross Rev", "Total", "Gross Revenue"),
        ("Net Rev", "Total", "Net Revenue"),
        ("CoS", "Total", "Cost of Sales"),
        ("GP", "Total", "**Gross Profit**"),
        ("OpEx", "Total", "Operating Expenses"),
        ("EBITDA", "Total", "**EBITDA**"),
    ]

    table_rows = []
    for metric, bu, label in metrics_for_table:
        row = {"Metric": label}
        for m in ytd_months:
            actual = get_val(metric, bu, "actual", m)
            aop = get_val(metric, bu, "aop", m)
            var_pct = ((actual - aop) / abs(aop) * 100) if aop != 0 else 0
            row[f"{m} Actual"] = format_money_short(actual)
            row[f"{m} AOP"] = format_money_short(aop)
            row[f"{m} Var%"] = f"{var_pct:+.0f}%"
        # YTD
        ytd_actual = sum(get_val(metric, bu, "actual", m) for m in ytd_months)
        ytd_aop = sum(get_val(metric, bu, "aop", m) for m in ytd_months)
        ytd_var_pct = ((ytd_actual - ytd_aop) / abs(ytd_aop) * 100) if ytd_aop != 0 else 0
        row["YTD Actual"] = format_money_short(ytd_actual)
        row["YTD AOP"] = format_money_short(ytd_aop)
        row["YTD Var%"] = f"{ytd_var_pct:+.0f}%"
        table_rows.append(row)

    pnl_table = pd.DataFrame(table_rows)

    def var_color(val):
        try:
            v = float(str(val).replace('%', '').replace('+', ''))
            if v > 5:
                return "color: #10B981"
            elif v < -5:
                return "color: #EF4444"
            return ""
        except:
            return ""

    def var_color_dollar(val):
        """Color dollar variance values: positive=green, negative=red."""
        try:
            s = str(val).replace('$', '').replace(',', '').replace('K', '').replace('M', '')
            v = float(s)
            if v > 0:
                return "color: #10B981"
            elif v < 0:
                return "color: #EF4444"
            return ""
        except:
            return ""

    def ytd_bg(val):
        return "background-color: #1E293B"

    var_cols = [c for c in pnl_table.columns if "Var%" in c]
    ytd_cols = [c for c in pnl_table.columns if c.startswith("YTD")]
    styled_pnl = (pnl_table.style
        .map(var_color, subset=var_cols)
        .map(ytd_bg, subset=ytd_cols)
    )
    st.dataframe(styled_pnl, use_container_width=True, hide_index=True)

    # ── GP by BU — Actuals vs AOP ────────────────────────────────────────
    st.markdown("### Gross Profit by Business Unit")

    bus = ["ABU", "Marketplace", "EBU", "Platform"]

    col_chart, col_table = st.columns([3, 2])

    with col_chart:
        bu_gp_data = []
        for bu in bus:
            actual = sum(get_val("GP", bu, "actual", m) for m in ytd_months)
            aop = sum(get_val("GP", bu, "aop", m) for m in ytd_months)
            bu_gp_data.append({"BU": bu, "Actual": actual, "AOP": aop})

        bu_gp_df = pd.DataFrame(bu_gp_data)

        fig_bu = go.Figure()
        fig_bu.add_trace(go.Bar(x=bus, y=bu_gp_df["AOP"], name="AOP", marker_color="#374151"))
        fig_bu.add_trace(go.Bar(x=bus, y=bu_gp_df["Actual"], name="Actual",
                                 marker_color=["#10B981" if a >= p else "#EF4444"
                                                for a, p in zip(bu_gp_df["Actual"], bu_gp_df["AOP"])]))
        fig_bu.update_layout(barmode="group", height=350, template="plotly_dark",
                              yaxis_title="Gross Profit ($)", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_bu, use_container_width=True)

    with col_table:
        bu_detail_rows = []
        for bu in bus:
            actual = sum(get_val("GP", bu, "actual", m) for m in ytd_months)
            aop = sum(get_val("GP", bu, "aop", m) for m in ytd_months)
            var = actual - aop
            var_pct = (var / abs(aop) * 100) if aop != 0 else 0
            # GP margin for BU
            rev_actual = sum(get_val("Net Rev", bu, "actual", m) for m in ytd_months)
            gp_margin = (actual / rev_actual * 100) if rev_actual != 0 else 0
            bu_detail_rows.append({
                "BU": bu,
                "GP Actual": format_money(actual),
                "GP AOP": format_money(aop),
                "Variance": format_money(var),
                "Var %": f"{var_pct:+.0f}%",
                "GP Margin": f"{gp_margin:.0f}%",
            })
        st.dataframe(pd.DataFrame(bu_detail_rows), use_container_width=True, hide_index=True)

    # ── Monthly GP Trend — Actual vs AOP ─────────────────────────────────
    st.markdown("### Monthly GP Trend — Actual vs AOP")

    fig_gp_trend = go.Figure()
    actual_vals = [get_val("GP", "Total", "actual", m) for m in MONTHS]
    aop_vals = [get_val("GP", "Total", "aop", m) for m in MONTHS]

    # Only show months with data
    active_months = [m for m, v in zip(MONTHS, actual_vals) if v != 0]
    active_actuals = [v for v in actual_vals if v != 0]
    active_aop = [aop_vals[i] for i, v in enumerate(actual_vals) if v != 0]

    fig_gp_trend.add_trace(go.Bar(x=active_months, y=active_aop, name="AOP", marker_color="#374151"))
    fig_gp_trend.add_trace(go.Bar(x=active_months, y=active_actuals, name="Actual",
                                   marker_color=["#10B981" if a >= p else "#EF4444"
                                                  for a, p in zip(active_actuals, active_aop)]))
    fig_gp_trend.update_layout(barmode="group", height=350, template="plotly_dark",
                                yaxis_title="Gross Profit ($)", margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_gp_trend, use_container_width=True)

    # ── Operating Expenses Breakdown ─────────────────────────────────────
    st.markdown("### Operating Expenses Breakdown")

    opex_categories = [
        ("HC Fixed", "S&M", "S&M"),
        ("HC Fixed", "Delivery", "Delivery"),
        ("HC Fixed", "Tech", "Tech"),
        ("HC Fixed", "G&A", "G&A"),
        ("HC Variable", "Total", "Variable HC"),
        ("Other Exp", "Total", "Other Expenses"),
    ]

    opex_col1, opex_col2 = st.columns([3, 2])

    with opex_col1:
        opex_data = []
        for metric, bu, label in opex_categories:
            actual = sum(get_val(metric, bu, "actual", m) for m in ytd_months)
            if actual > 0:
                opex_data.append({"Category": label, "Amount": actual})

        if opex_data:
            opex_df = pd.DataFrame(opex_data).sort_values("Amount", ascending=True)
            fig_opex = px.bar(opex_df, x="Amount", y="Category", orientation="h",
                               text="Amount", color_discrete_sequence=["#7C3AED"])
            fig_opex.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            fig_opex.update_layout(height=300, template="plotly_dark",
                                    margin=dict(l=20, r=80, t=20, b=20))
            st.plotly_chart(fig_opex, use_container_width=True)

    with opex_col2:
        opex_table = []
        for metric, bu, label in opex_categories:
            row = {"Category": label}
            for m in ytd_months:
                row[m] = format_money_short(get_val(metric, bu, "actual", m))
            ytd_act = sum(get_val(metric, bu, "actual", m) for m in ytd_months)
            ytd_aop_val = sum(get_val(metric, bu, "aop", m) for m in ytd_months)
            row["YTD"] = format_money_short(ytd_act)
            row["AOP"] = format_money_short(ytd_aop_val)
            var = ytd_act - ytd_aop_val
            row["Var"] = format_money_short(var)
            opex_table.append(row)
        # Total row
        total_row = {"Category": "**Total OpEx**"}
        for m in ytd_months:
            total_row[m] = format_money_short(get_val("OpEx", "Total", "actual", m))
        total_row["YTD"] = format_money_short(opex_ytd)
        total_row["AOP"] = format_money_short(opex_aop_ytd)
        total_row["Var"] = format_money_short(opex_ytd - opex_aop_ytd)
        opex_table.append(total_row)

        opex_df = pd.DataFrame(opex_table)
        ytd_opex_cols = [c for c in opex_df.columns if c in ["YTD", "AOP", "Var"]]
        styled_opex = (opex_df.style
            .map(ytd_bg, subset=ytd_opex_cols)
            .map(var_color_dollar, subset=["Var"])
        )
        st.dataframe(styled_opex, use_container_width=True, hide_index=True)

    # ── EBITDA Bridge ────────────────────────────────────────────────────
    st.markdown("### EBITDA Bridge (YTD)")

    fig_bridge = go.Figure(go.Waterfall(
        orientation="v",
        x=["Net Revenue", "Cost of Sales", "Gross Profit", "OpEx", "EBITDA"],
        y=[rev_ytd, -sum(get_val("CoS", "Total", "actual", m) for m in ytd_months),
           0, -opex_ytd, 0],
        measure=["absolute", "relative", "total", "relative", "total"],
        connector=dict(line=dict(color="#374151")),
        increasing=dict(marker=dict(color="#10B981")),
        decreasing=dict(marker=dict(color="#EF4444")),
        totals=dict(marker=dict(color="#4F46E5")),
        text=[format_money(rev_ytd),
              format_money(sum(get_val("CoS", "Total", "actual", m) for m in ytd_months)),
              format_money(gp_ytd),
              format_money(opex_ytd),
              format_money(ebitda_ytd)],
        textposition="outside",
    ))
    fig_bridge.update_layout(height=400, template="plotly_dark",
                              margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_bridge, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADCOUNT & COST ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Headcount & Cost Analysis")
st.caption("Source: HC Master (Drive) — latest monthly tab")

@st.cache_data(ttl=3600)
def load_headcount():
    try:
        from services.sheets_client import fetch_headcount
        return fetch_headcount(), None
    except Exception as e:
        return pd.DataFrame(), f"{type(e).__name__}: {e}"

hc_raw, hc_err = load_headcount()

if hc_raw.empty:
    if hc_err:
        st.error(f"Headcount load failed — {hc_err}")
    else:
        st.info("No headcount data available. Set `HC_SHEET_ID` in secrets to the Drive file ID of the HC Master .xlsx, and share the file with the service account.")
else:
    # Some HC headers have trailing spaces (e.g. "BU "). Strip them so col_map
    # lookups (built from stripped headers below) match real DataFrame columns.
    hc_raw = hc_raw.rename(columns=lambda c: str(c).strip())

    # Column mapping based on sheet structure
    col_map = {}
    headers = list(hc_raw.columns)
    for i, h in enumerate(headers):
        hl = h.lower()
        if 'name of staff' in hl or h == 'Name of staff':
            col_map['name'] = h
        elif 'status' == hl:
            col_map['status'] = h
        elif 'division' == hl:
            col_map['division'] = h
        elif 'country' == hl:
            col_map['country'] = h
        elif 'location' == hl:
            col_map['location'] = h
        elif 'department' == hl:
            col_map['department'] = h
        elif 'title' == hl:
            col_map['title'] = h
        elif 'type' == hl:
            col_map['type'] = h
        elif 'usd monthly fixed pay' in hl:
            col_map['monthly_usd'] = h
        elif 'usd annual fixed pay' in hl:
            col_map['annual_fixed_usd'] = h
        elif 'usd annual variable pay' in hl:
            col_map['annual_var_usd'] = h
        elif 'total compensation (usd)' in hl:
            col_map['total_comp_usd'] = h
        elif h.strip() == 'BU' or h.strip() == 'BU ':
            col_map['bu'] = h
        elif 'bu mapping' in hl:
            col_map['bu_mapping'] = h
        elif 'bu head' in hl:
            col_map['bu_head'] = h
        elif 'gender' == hl:
            col_map['gender'] = h
        elif 'start date' in hl:
            col_map['start_date'] = h

    def safe_float(val):
        s = str(val).replace(',', '').replace('"', '').replace('$', '').strip()
        try:
            return float(s)
        except:
            return 0.0

    hc = hc_raw.copy()

    # Parse USD compensation columns
    for key in ['monthly_usd', 'annual_fixed_usd', 'annual_var_usd', 'total_comp_usd']:
        if key in col_map:
            hc[col_map[key]] = hc[col_map[key]].apply(safe_float)

    # Filter active employees
    if 'status' in col_map:
        active = hc[hc[col_map['status']].str.strip().str.lower() == 'active'].copy()
        exited = hc[hc[col_map['status']].str.strip().str.lower() == 'exit'].copy()
    else:
        active = hc.copy()
        exited = pd.DataFrame()

    total_active = len(active)
    total_exited = len(exited)

    # ── KPI Cards ────────────────────────────────────────────────────
    monthly_burn = active[col_map['monthly_usd']].sum() if 'monthly_usd' in col_map else 0
    annual_fixed = active[col_map['annual_fixed_usd']].sum() if 'annual_fixed_usd' in col_map else 0
    annual_total = active[col_map['total_comp_usd']].sum() if 'total_comp_usd' in col_map else 0

    hc1, hc2, hc3, hc4 = st.columns(4)
    with hc1:
        st.metric("Active Headcount", total_active)
    with hc2:
        st.metric("Monthly Payroll", format_money(monthly_burn))
    with hc3:
        st.metric("Annual Fixed Cost", format_money(annual_fixed))
    with hc4:
        st.metric("Exits (YTD+)", total_exited)

    hc_tab_summary, hc_tab_bu, hc_tab_div = st.tabs(["📊 HC Summary", "💵 Cost by BU", "🏢 Solutions vs Platform"])

    # ── HC Summary Tab ──────────────────────────────────────────────
    with hc_tab_summary:
        hc_s1, hc_s2 = st.columns(2)

        with hc_s1:
            # By Department
            if 'bu' in col_map:
                st.markdown("#### Headcount by BU")
                bu_hc = active.groupby(col_map['bu']).size().reset_index(name='Count')
                bu_hc = bu_hc.sort_values('Count', ascending=False)
                bu_hc = bu_hc[bu_hc[col_map['bu']].str.strip() != '']
                fig_hc_bu = px.bar(bu_hc, x=col_map['bu'], y='Count',
                                   color_discrete_sequence=["#4F46E5"],
                                   text='Count')
                fig_hc_bu.update_traces(textposition='outside')
                fig_hc_bu.update_layout(height=350, template="plotly_dark",
                                        xaxis_title="", yaxis_title="Employees",
                                        margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_hc_bu, use_container_width=True)

        with hc_s2:
            # By Country
            if 'country' in col_map:
                st.markdown("#### Headcount by Country")
                country_hc = active.groupby(col_map['country']).size().reset_index(name='Count')
                country_hc = country_hc.sort_values('Count', ascending=False)
                country_hc = country_hc[country_hc[col_map['country']].str.strip() != '']
                fig_hc_country = px.pie(country_hc, names=col_map['country'], values='Count',
                                        color_discrete_sequence=px.colors.qualitative.Set2,
                                        hole=0.4)
                fig_hc_country.update_layout(height=350, template="plotly_dark",
                                              margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_hc_country, use_container_width=True)

        # By BU Head
        if 'bu_mapping' in col_map:
            st.markdown("#### Headcount by BU Head")
            head_hc = active.groupby(col_map['bu_mapping']).size().reset_index(name='Count')
            head_hc = head_hc.sort_values('Count', ascending=False)
            head_hc = head_hc[head_hc[col_map['bu_mapping']].str.strip() != '']
            st.dataframe(head_hc, use_container_width=True, hide_index=True)

    # ── Cost by BU Tab ──────────────────────────────────────────────
    with hc_tab_bu:
        if 'bu' in col_map and 'monthly_usd' in col_map:
            st.markdown("#### Monthly Payroll Cost by BU")

            bu_cost = active.groupby(col_map['bu']).agg(
                Headcount=(col_map['name'] if 'name' in col_map else col_map['bu'], 'count'),
                Monthly_USD=(col_map['monthly_usd'], 'sum'),
                Annual_Fixed_USD=(col_map['annual_fixed_usd'], 'sum') if 'annual_fixed_usd' in col_map else (col_map['monthly_usd'], lambda x: x.sum() * 12),
            ).reset_index()
            bu_cost = bu_cost[bu_cost[col_map['bu']].str.strip() != '']
            bu_cost = bu_cost.sort_values('Monthly_USD', ascending=False)
            bu_cost['Avg Monthly/Head'] = bu_cost['Monthly_USD'] / bu_cost['Headcount']

            # Chart
            fig_cost = go.Figure()
            fig_cost.add_trace(go.Bar(
                x=bu_cost[col_map['bu']], y=bu_cost['Monthly_USD'],
                name="Monthly Payroll",
                marker_color="#7C3AED",
                text=[format_money(v) for v in bu_cost['Monthly_USD']],
                textposition='outside',
            ))
            fig_cost.update_layout(height=400, template="plotly_dark",
                                    yaxis_title="Monthly Cost (USD)",
                                    margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_cost, use_container_width=True)

            # Table
            bu_display = bu_cost.copy()
            bu_display.columns = [col_map['bu'], 'HC', 'Monthly Cost', 'Annual Fixed', 'Avg/Head']
            bu_display['Monthly Cost'] = bu_display['Monthly Cost'].apply(format_money)
            bu_display['Annual Fixed'] = bu_display['Annual Fixed'].apply(format_money)
            bu_display['Avg/Head'] = bu_display['Avg/Head'].apply(format_money)
            st.dataframe(bu_display, use_container_width=True, hide_index=True)

            # Total row
            st.caption(f"**Total:** {total_active} employees | Monthly: {format_money(monthly_burn)} | Annual Fixed: {format_money(annual_fixed)}")
        else:
            st.info("BU or compensation columns not found in headcount data.")

    # ── Solutions vs Platform Tab ───────────────────────────────────
    with hc_tab_div:
        if 'division' in col_map:
            st.markdown("#### Solutions (incl. Turbo) vs Platform (incl. EBU)")
            st.caption("Based on Division column — Solutions includes MP, ABU, Tech, FinOps; Platform includes EBU, GAF, Product, Shared")

            def classify_division(div):
                d = str(div).strip().replace('\\', '')
                if d.startswith('Solution'):
                    return 'Solutions'
                elif d.startswith('Platform'):
                    return 'Platform'
                elif d in ('Founders', 'G&A', 'G\\&A'):
                    return 'G&A / Founders'
                return 'Other'

            def get_sub_division(div):
                d = str(div).strip().replace('\\', '')
                if '_' in d:
                    return d.split('_', 1)[1]
                return d

            active['_group'] = active[col_map['division']].apply(classify_division)
            active['_sub'] = active[col_map['division']].apply(get_sub_division)

            # Top-level comparison
            group_data = active.groupby('_group').agg(
                HC=(col_map['division'], 'count'),
                Monthly_USD=(col_map['monthly_usd'], 'sum') if 'monthly_usd' in col_map else (col_map['division'], 'count'),
                Annual_Fixed=(col_map['annual_fixed_usd'], 'sum') if 'annual_fixed_usd' in col_map else (col_map['division'], 'count'),
            ).reset_index()

            div_c1, div_c2 = st.columns(2)

            with div_c1:
                fig_div_hc = go.Figure()
                colors = {'Solutions': '#4F46E5', 'Platform': '#7C3AED', 'G&A / Founders': '#6B7280', 'Other': '#9CA3AF'}
                fig_div_hc.add_trace(go.Bar(
                    x=group_data['_group'], y=group_data['HC'],
                    marker_color=[colors.get(g, '#9CA3AF') for g in group_data['_group']],
                    text=group_data['HC'], textposition='outside',
                ))
                fig_div_hc.update_layout(height=300, template="plotly_dark",
                                          title="Headcount", yaxis_title="Employees",
                                          margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_div_hc, use_container_width=True)

            with div_c2:
                if 'monthly_usd' in col_map:
                    fig_div_cost = go.Figure()
                    fig_div_cost.add_trace(go.Bar(
                        x=group_data['_group'], y=group_data['Monthly_USD'],
                        marker_color=[colors.get(g, '#9CA3AF') for g in group_data['_group']],
                        text=[format_money(v) for v in group_data['Monthly_USD']],
                        textposition='outside',
                    ))
                    fig_div_cost.update_layout(height=300, template="plotly_dark",
                                                title="Monthly Payroll", yaxis_title="USD",
                                                margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig_div_cost, use_container_width=True)

            # Summary table
            group_display = group_data.copy()
            group_display.columns = ['Group', 'HC', 'Monthly Cost', 'Annual Fixed']
            if 'monthly_usd' in col_map:
                group_display['Monthly Cost'] = group_display['Monthly Cost'].apply(format_money)
                group_display['Annual Fixed'] = group_display['Annual Fixed'].apply(format_money)
                group_display['% of Total HC'] = (group_data['HC'] / total_active * 100).apply(lambda v: f"{v:.0f}%")
            st.dataframe(group_display, use_container_width=True, hide_index=True)

            # Sub-division breakdown
            st.markdown("#### Breakdown by Sub-Division")

            sub_data = active.groupby(['_group', '_sub']).agg(
                HC=(col_map['division'], 'count'),
                Monthly_USD=(col_map['monthly_usd'], 'sum') if 'monthly_usd' in col_map else (col_map['division'], 'count'),
            ).reset_index().sort_values(['_group', 'Monthly_USD'], ascending=[True, False])

            sol_col, plat_col = st.columns(2)

            with sol_col:
                st.markdown("**Solutions**")
                sol_sub = sub_data[sub_data['_group'] == 'Solutions'].copy()
                if not sol_sub.empty:
                    sol_display = sol_sub[['_sub', 'HC', 'Monthly_USD']].copy()
                    sol_display.columns = ['Sub-Division', 'HC', 'Monthly Cost']
                    sol_display['Monthly Cost'] = sol_display['Monthly Cost'].apply(format_money)
                    st.dataframe(sol_display, use_container_width=True, hide_index=True)

            with plat_col:
                st.markdown("**Platform**")
                plat_sub = sub_data[sub_data['_group'] == 'Platform'].copy()
                if not plat_sub.empty:
                    plat_display = plat_sub[['_sub', 'HC', 'Monthly_USD']].copy()
                    plat_display.columns = ['Sub-Division', 'HC', 'Monthly Cost']
                    plat_display['Monthly Cost'] = plat_display['Monthly Cost'].apply(format_money)
                    st.dataframe(plat_display, use_container_width=True, hide_index=True)

            # Clean up temp columns
            active.drop(columns=['_group', '_sub'], inplace=True, errors='ignore')
        else:
            st.info("Division column not found in headcount data.")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP AR BY BU
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Group AR by BU")
st.caption("Source of truth: Finance AR Sheet | Latest weekly snapshot")

@st.cache_data(ttl=3600)
def load_ar_data():
    """Load AR data from Google Sheets — latest weekly tab."""
    try:
        from services.sheets_client import fetch_ar_by_bu
        df = fetch_ar_by_bu()
        return df
    except Exception:
        return pd.DataFrame()

ar_raw = load_ar_data()

if ar_raw.empty:
    st.info("No AR data available. Ensure the AR sheet is shared with the service account.")
else:
    def parse_ar_val(s):
        """Parse AR dollar values (with commas, dashes, negatives)."""
        s = str(s).strip()
        if s in ("", "-", "–", "—"):
            return 0.0
        s = s.replace(",", "").replace("$", "")
        try:
            return float(s)
        except:
            return 0.0

    # ── Parse the two sections: India (header row 5, data 6+) and SEA (header row 180, data 181+)
    # India header at row 5: Business Unit, Region, Customer Name, Not billed, Billed not due,
    #   due < 180 days, due > 180 days, Total billed OS, Total receivable, Bad debt provision, Net receivable
    # SEA header at row 180: same structure but different aging labels

    india_customers = []
    sea_customers = []

    for i in range(6, len(ar_raw)):
        row = ar_raw.iloc[i]
        bu = str(row.iloc[0]).strip() if len(row) > 0 else ""
        region = str(row.iloc[1]).strip() if len(row) > 1 else ""
        customer = str(row.iloc[2]).strip() if len(row) > 2 else ""

        if not bu or bu == "Business Unit":
            # Could be the SEA header row — check for SEA section
            if customer == "Customer Name":
                continue
            continue

        net_recv = parse_ar_val(row.iloc[10]) if len(row) > 10 else 0
        not_billed = parse_ar_val(row.iloc[3]) if len(row) > 3 else 0
        billed_not_due = parse_ar_val(row.iloc[4]) if len(row) > 4 else 0
        due_lt_180 = parse_ar_val(row.iloc[5]) if len(row) > 5 else 0
        due_gt_180 = parse_ar_val(row.iloc[6]) if len(row) > 6 else 0
        total_billed = parse_ar_val(row.iloc[7]) if len(row) > 7 else 0
        total_recv = parse_ar_val(row.iloc[8]) if len(row) > 8 else 0
        bad_debt = parse_ar_val(row.iloc[9]) if len(row) > 9 else 0

        # Normalize BU names — SEA BUs have region appended (e.g. "ABU SEA", "MP SEA")
        bu_clean = bu.replace(" SEA", "").replace("/SaaS", "").replace("/MP", "")
        if bu_clean == "SAAS" or bu_clean == "SaaS":
            bu_clean = "SaaS"

        entry = {
            "BU": bu_clean,
            "Region": region if region else ("SEA" if "SEA" in bu else "India"),
            "Customer": customer,
            "Not Billed": not_billed,
            "Billed Not Due": billed_not_due,
            "Due <180d": due_lt_180,
            "Due >180d": due_gt_180,
            "Total Billed OS": total_billed,
            "Total Receivable": total_recv,
            "Bad Debt Provision": bad_debt,
            "Net Receivable": net_recv,
        }

        if region == "India":
            india_customers.append(entry)
        elif region == "SEA":
            sea_customers.append(entry)
        else:
            # Infer from BU name
            if "SEA" in bu:
                entry["Region"] = "SEA"
                sea_customers.append(entry)
            else:
                entry["Region"] = "India"
                india_customers.append(entry)

    all_customers = india_customers + sea_customers
    ar_df = pd.DataFrame(all_customers)

    if not ar_df.empty:
        # Filter to customers with non-zero receivables
        ar_active = ar_df[ar_df["Net Receivable"] != 0].copy()

        # ── Summary KPIs ─────────────────────────────────────────────────
        total_ar = ar_active["Net Receivable"].sum()
        india_ar = ar_active[ar_active["Region"] == "India"]["Net Receivable"].sum()
        sea_ar = ar_active[ar_active["Region"] == "SEA"]["Net Receivable"].sum()
        total_overdue = ar_active["Due >180d"].sum()
        total_bad_debt = ar_active["Bad Debt Provision"].sum()

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.metric("Total Net AR", format_money(total_ar))
        with k2:
            st.metric("India AR", format_money(india_ar))
        with k3:
            st.metric("SEA AR", format_money(sea_ar))
        with k4:
            st.metric("Overdue >180d", format_money(total_overdue),
                       delta=f"{total_overdue/total_ar*100:.0f}% of AR" if total_ar else "0%",
                       delta_color="inverse")
        with k5:
            st.metric("Bad Debt Provision", format_money(total_bad_debt),
                       delta_color="inverse")

        # ── AR by BU — chart + table ─────────────────────────────────────
        ar_col1, ar_col2 = st.columns([3, 2])

        with ar_col1:
            st.markdown("#### AR by Business Unit")
            bu_ar = ar_active.groupby("BU").agg(
                Net_AR=("Net Receivable", "sum"),
                Overdue_180=("Due >180d", "sum"),
                Customers=("Customer", "count"),
            ).reset_index().sort_values("Net_AR", ascending=False)

            fig_ar_bu = go.Figure()
            fig_ar_bu.add_trace(go.Bar(
                x=bu_ar["BU"], y=bu_ar["Net_AR"], name="Net AR",
                marker_color="#4F46E5",
                text=[format_money(v) for v in bu_ar["Net_AR"]],
                textposition="outside",
            ))
            fig_ar_bu.add_trace(go.Bar(
                x=bu_ar["BU"], y=bu_ar["Overdue_180"], name="Overdue >180d",
                marker_color="#EF4444",
                text=[format_money(v) for v in bu_ar["Overdue_180"]],
                textposition="outside",
            ))
            fig_ar_bu.update_layout(barmode="group", height=350, template="plotly_dark",
                                     yaxis_title="Amount ($)", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_ar_bu, use_container_width=True)

        with ar_col2:
            st.markdown("#### BU Summary")
            bu_summary = []
            for _, r in bu_ar.iterrows():
                overdue_pct = (r["Overdue_180"] / r["Net_AR"] * 100) if r["Net_AR"] else 0
                bu_summary.append({
                    "BU": r["BU"],
                    "Net AR": format_money(r["Net_AR"]),
                    ">180d": format_money(r["Overdue_180"]),
                    ">180d %": f"{overdue_pct:.0f}%",
                    "Customers": int(r["Customers"]),
                })
            st.dataframe(pd.DataFrame(bu_summary), use_container_width=True, hide_index=True)

        # ── AR by Region — Aging Breakdown ───────────────────────────────
        st.markdown("#### Aging Breakdown by Region")

        aging_col1, aging_col2 = st.columns(2)

        for region, col in [("India", aging_col1), ("SEA", aging_col2)]:
            with col:
                st.markdown(f"**{region}**")
                region_data = ar_active[ar_active["Region"] == region]
                if region_data.empty:
                    st.info(f"No {region} AR data")
                    continue

                aging = {
                    "Not Billed": region_data["Not Billed"].sum(),
                    "Billed Not Due": region_data["Billed Not Due"].sum(),
                    "Due <180d": region_data["Due <180d"].sum(),
                    "Due >180d": region_data["Due >180d"].sum(),
                }
                aging_df = pd.DataFrame([
                    {"Bucket": k, "Amount": v} for k, v in aging.items() if v != 0
                ])
                if not aging_df.empty:
                    fig_aging = px.pie(aging_df, names="Bucket", values="Amount",
                                       color_discrete_sequence=["#6366F1", "#10B981", "#F59E0B", "#EF4444"],
                                       hole=0.4)
                    fig_aging.update_layout(height=280, template="plotly_dark",
                                             margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_aging, use_container_width=True)

                    total_region = region_data["Net Receivable"].sum()
                    st.caption(f"Total Net AR: {format_money(total_region)} | "
                               f"{len(region_data)} customers with receivables")

        # ── Consolidate multi-entity customers ─────────────────────────────
        # Group entities that belong to the same parent company

        # Consolidation rules: (match_fn, display_name, default_bu)
        CONSOLIDATION_RULES = [
            # Schneider Electric India: SE Gurgaon, SE_India
            {
                "name": "Schneider Electric (India)",
                "bu": "EBU",
                "match": lambda n: n in ("SE Gurgaon", "SE_India"),
            },
            # Schneider Electric Global: SE Gulf, SE Hong Kong, SE Thailand, etc.
            {
                "name": "Schneider Electric (Global)",
                "bu": "EBU",
                "match": lambda n: (
                    (any(n.upper().startswith(p) for p in ("SE ", "SE_", "SCHNEIDER"))
                     and not any(n.upper().startswith(ex) for ex in ("SESA ", "SET ", "SEION"))
                     and n not in ("SE Gurgaon", "SE_India"))
                ),
            },
            # Puma Services + SaaS: Singapore, Philippines, Malaysia
            {
                "name": "Puma Services + SaaS",
                "bu": "MP/SaaS",
                "match": lambda n: n in (
                    "PUMA SOUTH EAST ASIA PTE LTD",
                    "PUMA SPORTS PHILIPPINES INC.",
                    "PUMA SPORTS GOODS SDN BHD",
                ),
            },
            # Puma SaaS: Vietnam, Thailand, Indonesia
            {
                "name": "Puma SaaS",
                "bu": "SaaS",
                "match": lambda n: "PUMA" in n.upper(),
            },
            # Avid Sports: Singapore, Thailand, Malaysia
            {
                "name": "Avid Sports (All Entities)",
                "bu": "SaaS",
                "match": lambda n: "AVID SPORTS" in n.upper(),
            },
            # MGI Distribution: Singapore, Malaysia
            {
                "name": "MGI Distribution (All Entities)",
                "bu": "MP",
                "match": lambda n: "MGI DISTRIBUTION" in n.upper(),
            },
            # Actually: Philippines, Singapore
            {
                "name": "Actually (All Entities)",
                "bu": "MP",
                "match": lambda n: n.upper().startswith("ACTUALLY"),
            },
            # Enviably Me: Singapore, Malaysia
            {
                "name": "Enviably Me (All Entities)",
                "bu": "MP",
                "match": lambda n: "ENVIABLY ME" in n.upper(),
            },
            # Luxolite: CV ROYAL BERSAMA ABADI (LUXOLITE), LUXOLITE (S) PTE. LTD.
            {
                "name": "Luxolite (All Entities)",
                "bu": "ABU",
                "match": lambda n: "LUXOLITE" in n.upper(),
            },
        ]

        def get_consolidated_name(customer_name):
            for rule in CONSOLIDATION_RULES:
                if rule["match"](customer_name):
                    return rule["name"], rule["bu"]
            return customer_name, None

        # Build consolidated AR view
        ar_consolidated = ar_active.copy()
        ar_consolidated["Display Name"] = ar_consolidated["Customer"].apply(
            lambda x: get_consolidated_name(x)[0]
        )

        # Aggregate multi-entity groups into single rows
        numeric_cols = ["Not Billed", "Billed Not Due", "Due <180d", "Due >180d",
                        "Total Billed OS", "Total Receivable", "Bad Debt Provision", "Net Receivable"]
        consolidated_names = [r["name"] for r in CONSOLIDATION_RULES]
        non_grouped = ar_consolidated[~ar_consolidated["Display Name"].isin(consolidated_names)]
        grouped_rows = []

        for rule in CONSOLIDATION_RULES:
            mask = ar_consolidated["Display Name"] == rule["name"]
            if not mask.any():
                continue
            group = ar_consolidated[mask]
            regions = group["Region"].unique()
            region_str = regions[0] if len(regions) == 1 else "Multi"
            agg_row = {
                "BU": rule["bu"],
                "Region": region_str,
                "Customer": rule["name"],
                "Display Name": rule["name"],
            }
            for col in numeric_cols:
                agg_row[col] = group[col].sum()
            grouped_rows.append(agg_row)

        if grouped_rows:
            ar_consolidated = pd.concat([
                non_grouped,
                pd.DataFrame(grouped_rows)
            ], ignore_index=True)

        # ── Separate good AR from bad debtors ────────────────────────────
        # Bad debtor = Bad Debt Provision >= 80% of Net Receivable and > $0
        ar_consolidated["Is Bad Debt"] = ar_consolidated.apply(
            lambda r: r["Bad Debt Provision"] >= r["Net Receivable"] * 0.8
                      and r["Bad Debt Provision"] > 0, axis=1
        )

        ar_good = ar_consolidated[~ar_consolidated["Is Bad Debt"]].copy()
        ar_bad = ar_consolidated[ar_consolidated["Is Bad Debt"]].copy()

        # ── Top 10 Customers by Region — Monthly AR & Aging ─────────────────

        @st.cache_data(ttl=3600)
        def load_ar_monthly():
            try:
                from services.sheets_client import fetch_ar_monthly_snapshots
                return fetch_ar_monthly_snapshots()
            except Exception:
                return {}

        monthly_snapshots = load_ar_monthly()

        # Parse each monthly snapshot to get per-customer Net Receivable
        def parse_monthly_ar(raw_df):
            """Parse a raw AR tab into {customer_name: net_receivable}."""
            cust_ar = {}
            if raw_df is None or raw_df.empty:
                return cust_ar
            for i in range(6, len(raw_df)):
                row = raw_df.iloc[i]
                bu = str(row.iloc[0]).strip() if len(row) > 0 else ""
                customer = str(row.iloc[2]).strip() if len(row) > 2 else ""
                if not bu or bu == "Business Unit" or not customer:
                    continue
                net_recv = parse_ar_val(row.iloc[10]) if len(row) > 10 else 0
                # Consolidate multi-entity customers
                key = get_consolidated_name(customer)[0]
                cust_ar[key] = cust_ar.get(key, 0) + net_recv
            return cust_ar

        monthly_ar = {}
        ar_months = ["Jan", "Feb", "Mar"]
        for m in ar_months:
            if m in monthly_snapshots:
                monthly_ar[m] = parse_monthly_ar(monthly_snapshots[m])

        def build_customer_table(customer_rows):
            rows = []
            for _, cust in customer_rows.iterrows():
                name = cust.get("Display Name", cust["Customer"])
                row = {
                    "Customer": name,
                    "BU": cust["BU"],
                }
                for m in ar_months:
                    if m in monthly_ar:
                        row[f"{m} AR"] = monthly_ar[m].get(name, 0)
                    else:
                        row[f"{m} AR"] = None

                month_vals = [row.get(f"{m} AR") for m in ar_months if row.get(f"{m} AR") is not None]
                if len(month_vals) >= 2:
                    row["Trend"] = month_vals[-1] - month_vals[0]
                else:
                    row["Trend"] = 0

                row["Not Due"] = cust["Billed Not Due"]
                row["<180d"] = cust["Due <180d"]
                row[">180d"] = cust["Due >180d"]
                rows.append(row)
            return pd.DataFrame(rows)

        def style_customer_table(df):
            display = df.copy()
            for m in ar_months:
                col = f"{m} AR"
                if col in display.columns:
                    display[col] = display[col].apply(
                        lambda v: format_money(v) if pd.notna(v) and v != 0 else "—"
                    )
            display["Trend"] = display["Trend"].apply(
                lambda v: f"{'↑' if v > 0 else '↓'} {format_money(abs(v))}" if v != 0 else "→ flat"
            )
            for col in ["Not Due", "<180d", ">180d"]:
                if col in display.columns:
                    display[col] = display[col].apply(
                        lambda v: format_money(v) if v != 0 else "—"
                    )

            def trend_color(val):
                if "↑" in str(val):
                    return "color: #EF4444"
                elif "↓" in str(val):
                    return "color: #10B981"
                return ""

            def overdue_color(val):
                if val and val != "—" and val != "$0":
                    return "color: #EF4444"
                return ""

            styled = display.style
            if "Trend" in display.columns:
                styled = styled.map(trend_color, subset=["Trend"])
            if ">180d" in display.columns:
                styled = styled.map(overdue_color, subset=[">180d"])
            return styled

        # Split good AR by region
        # "Multi" region = billed from India (e.g. Schneider Global) → show in India tab
        ar_good_india = ar_good[ar_good["Region"].isin(["India", "Multi"])].nlargest(10, "Net Receivable")
        ar_good_sea = ar_good[ar_good["Region"] == "SEA"].nlargest(10, "Net Receivable")

        india_tab, sea_tab = st.tabs(["🇮🇳 India — Top 10 Customers", "🌏 SEA — Top 10 Customers"])

        with india_tab:
            st.markdown("#### India — Top 10 Customers by Net Receivable")
            india_total = ar_good[ar_good["Region"] == "India"]["Net Receivable"].sum()
            st.caption(f"Total India AR (excl. bad debt): {format_money(india_total)}")
            if not ar_good_india.empty:
                india_df = build_customer_table(ar_good_india)
                st.dataframe(style_customer_table(india_df), use_container_width=True, hide_index=True)
            else:
                st.info("No India customer data")

        with sea_tab:
            st.markdown("#### SEA — Top 10 Customers by Net Receivable")
            sea_total = ar_good[ar_good["Region"].isin(["SEA", "Multi"])]["Net Receivable"].sum()
            st.caption(f"Total SEA AR (excl. bad debt): {format_money(sea_total)}")
            if not ar_good_sea.empty:
                sea_df = build_customer_table(ar_good_sea)
                st.dataframe(style_customer_table(sea_df), use_container_width=True, hide_index=True)
            else:
                st.info("No SEA customer data")

        # ── Bad Debtors ──────────────────────────────────────────────────
        if not ar_bad.empty:
            st.markdown("#### Bad Debtors")
            st.caption("Customers where bad debt provision ≥ 80% of net receivable")

            ar_bad_sorted = ar_bad.sort_values("Bad Debt Provision", ascending=False)
            bad_total = ar_bad_sorted["Bad Debt Provision"].sum()
            bad_ar_total = ar_bad_sorted["Net Receivable"].sum()

            bd1, bd2, bd3 = st.columns(3)
            with bd1:
                st.metric("Total Bad Debt Provision", format_money(bad_total))
            with bd2:
                st.metric("Bad Debt AR Outstanding", format_money(bad_ar_total))
            with bd3:
                st.metric("Bad Debt Customers", len(ar_bad_sorted))

            # Show top bad debtors
            bad_display = ar_bad_sorted[["Customer", "BU", "Region",
                                          "Net Receivable", "Bad Debt Provision",
                                          "Due >180d"]].head(15).copy()
            bad_display["Net Receivable"] = bad_display["Net Receivable"].apply(format_money)
            bad_display["Bad Debt Provision"] = bad_display["Bad Debt Provision"].apply(format_money)
            bad_display["Due >180d"] = bad_display["Due >180d"].apply(format_money)
            bad_display.columns = ["Customer", "BU", "Region", "Net AR", "Bad Debt", ">180d"]

            st.dataframe(bad_display, use_container_width=True, hide_index=True)

        # ── Concentration Risk ───────────────────────────────────────────
        st.markdown("#### Concentration Risk")
        sorted_ar = ar_active.sort_values("Net Receivable", ascending=False)
        top3_ar = sorted_ar.head(3)["Net Receivable"].sum()
        top5_ar = sorted_ar.head(5)["Net Receivable"].sum()
        top10_ar = sorted_ar.head(10)["Net Receivable"].sum()

        cr1, cr2, cr3, cr4 = st.columns(4)
        with cr1:
            st.metric("Top 3 Concentration", f"{top3_ar/total_ar*100:.0f}%" if total_ar else "0%",
                       help="% of total AR from top 3 customers")
        with cr2:
            st.metric("Top 5 Concentration", f"{top5_ar/total_ar*100:.0f}%" if total_ar else "0%")
        with cr3:
            st.metric("Top 10 Concentration", f"{top10_ar/total_ar*100:.0f}%" if total_ar else "0%")
        with cr4:
            st.metric("Active Customers", len(ar_active))
    else:
        st.info("No customer AR data parsed from the sheet.")
