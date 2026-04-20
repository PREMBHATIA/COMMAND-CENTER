"""Execute — Sprint, Infra, Performance & Support Tracker."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re

st.set_page_config(page_title="Execute | Graas", page_icon="⚙️", layout="wide")
st.markdown("## ⚙️ Execute — Engineering & Ops Tracker")
st.markdown("[Open Source Deck →](https://docs.google.com/presentation/d/1mWzpiiKM-or1NJJXOheL_9cE05bfHZhxnagr8AC_kkQ/edit)")

# ── Data Loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_execute_data():
    txt_path = Path.home() / "Downloads" / "Engg and Product 2026.txt"
    if txt_path.exists():
        with open(txt_path, "r") as f:
            return f.read()
    return ""

raw_text = load_execute_data()

if not raw_text:
    st.warning("No Execute data. Export the Engg & Product deck as .txt (File → Download → Plain text)")
    st.stop()

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ── Parse structured data from text ───────────────────────────────────────────

def parse_sprint_stories(text):
    """Extract JIRA stories with status from sprint updates."""
    stories = []
    # Match patterns like "TC-22792: Description" or "TC-22792 : Description"
    jira_pattern = re.compile(r'(TC-\d+)\s*:\s*(.+?)(?=TC-\d+|Spillover|Good to Release|$)', re.DOTALL)

    # Find status context
    lines = text.split('\n')
    current_status = ""
    current_epic = ""

    for line in lines:
        line_stripped = line.strip()
        if 'In Live' in line or 'In live' in line:
            current_status = "Live"
        elif 'In QA' in line:
            current_status = "In QA"
        elif 'In Progress' in line or 'In-Progress' in line:
            current_status = "In Progress"
        elif 'Ready for live' in line or 'Ready for Live' in line:
            current_status = "Ready for Live"
        elif 'Ready for QA' in line:
            current_status = "Ready for QA"
        elif 'Spillover' in line:
            current_status = "Spillover"
        elif line_stripped in ("Production", "Tech Implementations", "Finance", "OMS/IMS/CMS", "DKSH invoice"):
            current_epic = line_stripped

        matches = jira_pattern.findall(line)
        for jira_id, desc in matches:
            desc_clean = desc.strip().split('\n')[0].strip()
            if desc_clean and len(desc_clean) > 5:
                stories.append({
                    "jira_id": jira_id,
                    "description": desc_clean[:150],
                    "status": current_status or "Unknown",
                    "epic": current_epic or "General",
                })

    return stories

def parse_support_issues(text):
    """Extract support issues."""
    issues = []
    lines = text.split('\n')
    in_support = False

    for line in lines:
        if 'Support - Snapshot' in line or 'support tasks' in line.lower():
            in_support = True
            continue
        if in_support and line.strip() and not line.strip().startswith(('Total', 'Last Week', 'OverAll')):
            issue = line.strip()
            if len(issue) > 10 and issue[0].isupper():
                # Extract seller ID if present
                seller_match = re.search(r'(AAD\w+|GSK|GCK|GED|ILL|IGZ|FYW|FFH|HFC)', issue)
                seller = seller_match.group(1) if seller_match else ""
                issues.append({"issue": issue[:200], "seller": seller})
            if len(issues) > 20:
                break

    return issues

def parse_infra_costs(text):
    """Extract cost optimization and infra data."""
    costs = []
    lines = text.split('\n')
    in_cost = False

    for i, line in enumerate(lines):
        if 'Cost Optimization' in line or 'Cost Impact' in line:
            in_cost = True
            continue
        if in_cost:
            if line.strip().startswith(('1', '2', '3', '4', '5')):
                # Try to get the next lines as details
                desc = lines[i+1].strip() if i+1 < len(lines) else ""
                benefit = lines[i+2].strip() if i+2 < len(lines) else ""
                status_line = lines[i+3].strip() if i+3 < len(lines) else ""
                costs.append({
                    "activity": desc[:150] if desc else line.strip(),
                    "benefit": benefit[:150],
                    "status": status_line if status_line in ("Completed", "Pending", "In Progress", "Pending - On-Hold") else "",
                })

    return costs

def parse_migration_status(text):
    """Extract GCP → AWS migration phases."""
    phases = []
    lines = text.split('\n')
    in_migration = False

    for i, line in enumerate(lines):
        if 'GCP -> AWS Migration' in line:
            in_migration = True
            continue
        if in_migration and line.strip().startswith('Phase'):
            phase = line.strip()
            details = lines[i+1].strip() if i+1 < len(lines) else ""
            progress = lines[i+2].strip() if i+2 < len(lines) else ""
            status = lines[i+3].strip() if i+3 < len(lines) else ""
            phases.append({
                "phase": phase,
                "details": details[:150],
                "progress": progress[:150],
                "status": status,
            })

    return phases

def parse_infra_stories(text):
    """Extract GCP→AWS JIRA stories."""
    stories = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in ("P1", "P2", "P3"):
            priority = line
            jira_id = lines[i+1].strip() if i+1 < len(lines) else ""
            desc = lines[i+2].strip() if i+2 < len(lines) else ""
            assignee = lines[i+3].strip() if i+3 < len(lines) else ""
            if jira_id.startswith("TC-"):
                stories.append({
                    "priority": priority,
                    "jira_id": jira_id,
                    "description": desc[:150],
                    "assignee": assignee,
                })
            i += 4
        else:
            i += 1
    return stories

def parse_mongo_optimizations(text):
    """Extract MongoDB optimization items."""
    items = []
    lines = text.split('\n')
    in_mongo = False

    for i, line in enumerate(lines):
        if 'MongoDB Optimizations' in line:
            in_mongo = True
            continue
        if in_mongo and line.strip() in ("Epic", "Details", "Status", "Target"):
            continue
        if in_mongo:
            stripped = line.strip()
            if stripped in ("Housekeeping & Archival of data", "Cluster Consolidation",
                           "MongoDB Project merge 3 -> 1", "Cluster Migration & Optimization"):
                details = lines[i+1].strip() if i+1 < len(lines) else ""
                status = ""
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() in ("Done", "In Progress", "Completed"):
                        status = lines[j].strip()
                        break
                items.append({"epic": stripped, "details": details[:150], "status": status})
            if 'Samy' in stripped or 'Risk' in stripped:
                break

    return items

# Parse all sections
sprint_stories = parse_sprint_stories(raw_text)
support_issues = parse_support_issues(raw_text)
cost_items = parse_infra_costs(raw_text)
migration_phases = parse_migration_status(raw_text)
infra_stories = parse_infra_stories(raw_text)
mongo_items = parse_mongo_optimizations(raw_text)

# ══════════════════════════════════════════════════════════════════════════════

tab_sprint, tab_infra, tab_perf, tab_support = st.tabs([
    "🏃 Sprint Stories",
    "💰 Infra & Costs",
    "⚡ Performance",
    "🎫 Support Issues",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: SPRINT STORIES
# ══════════════════════════════════════════════════════════════════════════════

with tab_sprint:
    st.markdown("### Sprint 57 — Story Tracker")
    st.caption("Tracks which stories are moving, stuck, or spilling over")

    if sprint_stories:
        stories_df = pd.DataFrame(sprint_stories)

        # KPI cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Stories", len(stories_df))
        with c2:
            live = len(stories_df[stories_df["status"] == "Live"])
            st.metric("Live", live)
        with c3:
            in_progress = len(stories_df[stories_df["status"].isin(["In Progress", "In QA", "Ready for Live", "Ready for QA"])])
            st.metric("In Progress / QA", in_progress)
        with c4:
            spillover = len(stories_df[stories_df["status"] == "Spillover"])
            st.metric("Spillover", spillover, delta_color="inverse")

        # Status distribution
        status_counts = stories_df["status"].value_counts()
        fig_status = px.pie(
            names=status_counts.index, values=status_counts.values,
            color_discrete_sequence=["#10B981", "#06B6D4", "#F59E0B", "#EF4444", "#6B7280", "#4F46E5"],
        )
        fig_status.update_layout(height=300, template="plotly_dark")
        st.plotly_chart(fig_status, use_container_width=True)

        # Story table with color coding
        def status_color(val):
            colors = {
                "Live": "background-color: #065F46; color: white",
                "Ready for Live": "background-color: #064E3B; color: white",
                "In QA": "background-color: #1E40AF; color: white",
                "Ready for QA": "background-color: #1E3A5F; color: white",
                "In Progress": "background-color: #92400E; color: white",
                "Spillover": "background-color: #7F1D1D; color: white",
            }
            return colors.get(val, "")

        st.dataframe(
            stories_df[["jira_id", "description", "status", "epic"]]
            .rename(columns={"jira_id": "JIRA", "description": "Story", "status": "Status", "epic": "Epic"})
            .style.applymap(status_color, subset=["Status"]),
            use_container_width=True, hide_index=True, height=500,
        )

        # Spillover highlight
        spillovers = stories_df[stories_df["status"] == "Spillover"]
        if not spillovers.empty:
            st.markdown("### ⚠️ Spillover Stories")
            st.caption("These stories did not complete in the sprint — watch for repeats")
            for _, s in spillovers.iterrows():
                st.markdown(f"- **{s['jira_id']}**: {s['description']} ({s['epic']})")
    else:
        st.info("No sprint stories parsed. Check the source deck.")

    # Key customer updates
    st.markdown("### 🏢 Key Customer Updates")

    customer_updates = [
        {"customer": "Puma SaaS", "updates": "Return orders not pushed properly. ID - OOS issue investigating. Vend integration go-live after Laz bday. Account merge ongoing.", "status": "In Progress"},
        {"customer": "DKSH SG", "updates": "Live to Stage account (Hiruscar IKU, RECKITT, UNICHARM). UOM & Stock issues to discuss. UAT success - Live date TBD.", "status": "In Progress"},
        {"customer": "DKSH TH", "updates": "Return Tracking number to be pushed via API. Field creation needed from DKSH SAP side.", "status": "TBD"},
        {"customer": "WMS", "updates": "Update orders not happening - random misses (weekend issue).", "status": "Investigating"},
    ]
    st.dataframe(pd.DataFrame(customer_updates), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: INFRA & COSTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_infra:

    # ── Monthly Infrastructure Costs ──────────────────────────────────────────
    st.markdown("### Monthly Infrastructure Costs")
    st.caption("Source: Slide 31 — Cost Trends Overall")

    cost_months = ["Mar-25", "Apr-25", "May-25", "Jun-25", "Jul-25", "Aug-25", "Sep-25", "Oct-25", "Nov-25", "Dec-25", "Jan-26", "Feb-26"]

    cost_data = {
        "Month": cost_months,
        "GCP": [16778, 14401, 13866, 12310, 11744, 9651, 9642, 9191, 9173, 10039, 6218, 4048],
        "AWS": [11058, 11786, 14975, 15516, 14835, 13601, 12716, 14223, 17714, 14891, 17522, 13447],
        "Snowflake": [6528, 6103, 6875, 6507, 7725, 7759, 6738, 6132, 6748, 5778, 4740, 3846],
        "MongoDB": [9459, 9779, 11403, 11227, 10413, 10665, 9360, 10496, 8625, 9472, 10270, 8069],
    }
    cost_df = pd.DataFrame(cost_data)
    cost_df["Total"] = cost_df["GCP"] + cost_df["AWS"] + cost_df["Snowflake"] + cost_df["MongoDB"]

    # KPI Cards — latest month vs previous
    latest = cost_df.iloc[-1]
    prev = cost_df.iloc[-2]

    def cost_delta(curr, prev):
        change = curr - prev
        pct = change / prev * 100 if prev else 0
        return f"{pct:+.0f}%"

    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    with kc1:
        st.metric("Total (Feb-26)", f"${latest['Total']:,.0f}", cost_delta(latest['Total'], prev['Total']), delta_color="inverse")
    with kc2:
        st.metric("GCP", f"${latest['GCP']:,.0f}", cost_delta(latest['GCP'], prev['GCP']), delta_color="inverse")
    with kc3:
        st.metric("AWS", f"${latest['AWS']:,.0f}", cost_delta(latest['AWS'], prev['AWS']), delta_color="inverse")
    with kc4:
        st.metric("Snowflake", f"${latest['Snowflake']:,.0f}", cost_delta(latest['Snowflake'], prev['Snowflake']), delta_color="inverse")
    with kc5:
        st.metric("MongoDB", f"${latest['MongoDB']:,.0f}", cost_delta(latest['MongoDB'], prev['MongoDB']), delta_color="inverse")

    # Stacked area chart
    fig_cost = go.Figure()
    colors = {"GCP": "#4285F4", "AWS": "#FF9900", "Snowflake": "#29B5E8", "MongoDB": "#00ED64"}
    for platform in ["GCP", "AWS", "Snowflake", "MongoDB"]:
        fig_cost.add_trace(go.Scatter(
            x=cost_df["Month"], y=cost_df[platform],
            mode="lines", name=platform,
            stackgroup="one",
            line=dict(width=0.5, color=colors[platform]),
            fillcolor=colors[platform],
        ))

    fig_cost.update_layout(
        height=400, template="plotly_dark",
        yaxis_title="Monthly Cost ($)",
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_cost, use_container_width=True)

    # Platform breakdown chart — side by side
    st.markdown("### Platform Breakdown")
    col_trend1, col_trend2 = st.columns(2)

    with col_trend1:
        # GCP trending down (good — migration working)
        fig_gcp = go.Figure()
        fig_gcp.add_trace(go.Bar(x=cost_df["Month"], y=cost_df["GCP"], marker_color="#4285F4"))
        fig_gcp.update_layout(
            title="GCP — Trending Down ✅", height=280, template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20), yaxis_title="$",
        )
        st.plotly_chart(fig_gcp, use_container_width=True)

    with col_trend2:
        # AWS trending up (expected — taking over from GCP)
        fig_aws = go.Figure()
        fig_aws.add_trace(go.Bar(x=cost_df["Month"], y=cost_df["AWS"], marker_color="#FF9900"))
        fig_aws.update_layout(
            title="AWS — Migration Target", height=280, template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20), yaxis_title="$",
        )
        st.plotly_chart(fig_aws, use_container_width=True)

    col_trend3, col_trend4 = st.columns(2)

    with col_trend3:
        fig_sf = go.Figure()
        fig_sf.add_trace(go.Bar(x=cost_df["Month"], y=cost_df["Snowflake"], marker_color="#29B5E8"))
        fig_sf.update_layout(
            title="Snowflake", height=280, template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20), yaxis_title="$",
        )
        st.plotly_chart(fig_sf, use_container_width=True)

    with col_trend4:
        fig_mongo = go.Figure()
        fig_mongo.add_trace(go.Bar(x=cost_df["Month"], y=cost_df["MongoDB"], marker_color="#00ED64"))
        fig_mongo.update_layout(
            title="MongoDB", height=280, template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20), yaxis_title="$",
        )
        st.plotly_chart(fig_mongo, use_container_width=True)

    # Cost table
    with st.expander("📋 Full Cost Table"):
        display_cost = cost_df.copy()
        for col in ["GCP", "AWS", "Snowflake", "MongoDB", "Total"]:
            display_cost[col] = display_cost[col].apply(lambda x: f"${x:,.0f}")
        st.dataframe(display_cost, use_container_width=True, hide_index=True)

    # 12-month totals
    st.markdown("### 12-Month Totals (Mar 2025 — Feb 2026)")
    tc1, tc2, tc3, tc4, tc5 = st.columns(5)
    with tc1:
        st.metric("Total", "$494,064")
    with tc2:
        st.metric("GCP", "$127,063")
    with tc3:
        st.metric("AWS", "$172,284")
    with tc4:
        st.metric("Snowflake", "$75,478")
    with tc5:
        st.metric("MongoDB", "$119,240")

    st.markdown("---")

    # ── Migration Section (moved below costs) ─────────────────────────────────
    st.markdown("### GCP → AWS Migration")

    if migration_phases:
        mig_df = pd.DataFrame(migration_phases)

        def mig_status_color(val):
            if val == "Completed":
                return "background-color: #065F46; color: white"
            elif "Progress" in str(val):
                return "background-color: #92400E; color: white"
            return ""

        st.dataframe(
            mig_df.rename(columns={"phase": "Phase", "details": "Scope", "progress": "Progress", "status": "Status"})
            .style.applymap(mig_status_color, subset=["Status"]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No migration data parsed.")

    # Migration JIRA stories
    if infra_stories:
        st.markdown("### Infra JIRA Stories")

        infra_df = pd.DataFrame(infra_stories)

        def priority_color(val):
            if val == "P1":
                return "background-color: #7F1D1D; color: white"
            elif val == "P2":
                return "background-color: #92400E; color: white"
            return ""

        st.dataframe(
            infra_df.rename(columns={"priority": "Pri", "jira_id": "JIRA", "description": "Story", "assignee": "Assignee"})
            .style.applymap(priority_color, subset=["Pri"]),
            use_container_width=True, hide_index=True, height=400,
        )

    # MongoDB Optimizations
    if mongo_items:
        st.markdown("### MongoDB Optimizations")
        mongo_df = pd.DataFrame(mongo_items)
        st.dataframe(
            mongo_df.rename(columns={"epic": "Initiative", "details": "Details", "status": "Status"}),
            use_container_width=True, hide_index=True,
        )

    # Cost Optimization
    st.markdown("### Cost Optimization Initiatives")
    if cost_items:
        cost_df = pd.DataFrame(cost_items)
        st.dataframe(
            cost_df.rename(columns={"activity": "Activity", "benefit": "Benefit", "status": "Status"}),
            use_container_width=True, hide_index=True,
        )
    else:
        # Manual entries from the parsed text
        cost_manual = [
            {"Activity": "Shut-down Execute Pipeline for non-paid customers", "Benefit": "Reduced >50% of Execute jobs", "Status": "Completed"},
            {"Activity": "MongoDB Data cleanup & reindexing (offboarded)", "Benefit": "Reduced storage & IOPS", "Status": "Completed"},
            {"Activity": "Images cleanup for offboarded customers", "Benefit": "Bucket storage cost reduction", "Status": "On-Hold"},
            {"Activity": "Stop all unnecessary jobs on Sellinall host", "Benefit": "Decommissioned clusters", "Status": "Completed"},
            {"Activity": "Stop Webhooks (Zalora, Shopify, Woocommerce)", "Benefit": "Reduced traffic", "Status": "Completed"},
        ]
        st.dataframe(pd.DataFrame(cost_manual), use_container_width=True, hide_index=True)

    # Sprint cost allocation
    st.markdown("### Sprint Cost Allocation — Sprint 57")
    alloc = pd.DataFrame([
        {"Type": "CapEx", "Stories": 3, "Man Days": 10},
        {"Type": "OpEx", "Stories": 11, "Man Days": 39},
        {"Type": "Merchant", "Stories": 3, "Man Days": 9},
    ])

    ca1, ca2 = st.columns(2)
    with ca1:
        fig_alloc = px.pie(alloc, names="Type", values="Stories", title="By Stories",
                           color_discrete_sequence=["#4F46E5", "#7C3AED", "#10B981"])
        fig_alloc.update_layout(height=280, template="plotly_dark")
        st.plotly_chart(fig_alloc, use_container_width=True)
    with ca2:
        fig_days = px.pie(alloc, names="Type", values="Man Days", title="By Man Days",
                          color_discrete_sequence=["#4F46E5", "#7C3AED", "#10B981"])
        fig_days.update_layout(height=280, template="plotly_dark")
        st.plotly_chart(fig_days, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

with tab_perf:
    st.markdown("### Observability & Alerting Progress")

    alert_data = pd.DataFrame([
        {"Priority": "P0", "Required": 9, "Implemented": 6, "Complete": "67%"},
        {"Priority": "P1", "Required": "-", "Implemented": "-", "Complete": "TBD"},
        {"Priority": "P2", "Required": "-", "Implemented": "-", "Complete": "TBD"},
    ])
    st.dataframe(alert_data, use_container_width=True, hide_index=True)

    st.markdown("### Alerting Roadmap")
    roadmap = [
        {"Task": "Minimize/stop harsh alert noise", "Target": "10 Mar 2026", "Status": "Done"},
        {"Task": "Define error rates, traffic & heartbeat alerts", "Target": "13 Mar 2026", "Status": "Done"},
        {"Task": "Prioritise services", "Target": "17 Mar 2026", "Status": "Done"},
        {"Task": "Define alert requirements & criteria", "Target": "20 Mar 2026", "Status": "Done"},
    ]
    st.dataframe(pd.DataFrame(roadmap), use_container_width=True, hide_index=True)

    st.markdown("### 3/3 Sale Day Performance")
    st.markdown("**Total Orders: 102,661** | Managed Customer Orders: 64,892")

    sale_data = pd.DataFrame([
        {"Seller": "DKSH TH (CG)", "12.12 Orders": "12,719", "3.3 Orders": "10,666"},
        {"Seller": "Puma ID", "12.12 Orders": "13,167", "3.3 Orders": "10,427"},
        {"Seller": "DKSH ABBOTT", "12.12 Orders": "11,546", "3.3 Orders": "9,959"},
        {"Seller": "PUMA (SG,MY,PH)", "12.12 Orders": "25,436", "3.3 Orders": "12,872"},
        {"Seller": "Puma VN", "12.12 Orders": "15,727", "3.3 Orders": "5,569"},
        {"Seller": "PUMA TH", "12.12 Orders": "8,912", "3.3 Orders": "4,651"},
        {"Seller": "Kose", "12.12 Orders": "2,149", "3.3 Orders": "1,905"},
        {"Seller": "Haleon", "12.12 Orders": "1,919", "3.3 Orders": "1,519"},
        {"Seller": "DKSH MY", "12.12 Orders": "1,446", "3.3 Orders": "1,079"},
        {"Seller": "DKSH-UNICHARM", "12.12 Orders": "1,376", "3.3 Orders": "1,242"},
        {"Seller": "DKSH SG (CG)", "12.12 Orders": "1,037", "3.3 Orders": "816"},
    ])
    st.dataframe(sale_data, use_container_width=True, hide_index=True)

    st.markdown("**What worked:** Systems scaled smoothly, team monitored with hourly Slack updates, no major order/inventory issues.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: SUPPORT ISSUES
# ══════════════════════════════════════════════════════════════════════════════

with tab_support:
    st.markdown("### Execute Support Snapshot")

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("Total Issues (2026)", "235")
    with sc2:
        st.metric("Last Week Tickets", "18")
    with sc3:
        st.metric("CSM Tickets (Last Week)", "1")

    st.markdown("### Last Week's Key Issues")

    last_week_issues = [
        {"Issue": "FYW - Status Changing via TC not working", "Seller": "FYW", "Type": "Execute"},
        {"Issue": "AADCT - Order status not getting updated properly", "Seller": "AADCT", "Type": "Execute"},
        {"Issue": "GSK - WMS failed tab, edit SKU shows access denied", "Seller": "GSK", "Type": "Execute"},
        {"Issue": "Root cause investigation: order not moved to RTS in TC", "Seller": "-", "Type": "CSM"},
    ]
    st.dataframe(pd.DataFrame(last_week_issues), use_container_width=True, hide_index=True)

    st.markdown("### FinOps — Weekly Issues & Fixes")
    st.caption("Key support items from FinOps × Fintech")

    finops_issues = [
        {"Issue": "Shopee adjustment fee mapping — incorrect fee mapping causing MP sold price mismatches", "Status": "Open"},
        {"Issue": "Lazada return order scenarios — paymentMethod not updated, reconciliation stuck", "Status": "Open"},
        {"Issue": "Exchange rate update — cannot modify from frontend, done via API", "Status": "Fixed"},
        {"Issue": "Lazada feeType mismatch (Reverse) — wrong feeType for Funded Commission", "Status": "Open"},
        {"Issue": "Lazada feeType missing — empty for SVC Sponsored Affiliate Rebate", "Status": "Open"},
        {"Issue": "isReturnExempt flag — Graas commission incorrectly set to zero on cancel", "Status": "Open"},
        {"Issue": "Shopee adjustment orders — isReturnExempt flag not working for feeType=others", "Status": "Open"},
        {"Issue": "HFC SaaS Commission line not capturing in admin", "Status": "Open"},
        {"Issue": "Shopee getSettlement — slow import + duplicate records", "Status": "Fixed"},
        {"Issue": "Lazada marketplace commission mismatch due to feeType others", "Status": "Open"},
        {"Issue": "TikTok cancelled orders — fields unupdated in siASettlement", "Status": "Open"},
        {"Issue": "Enabled reference invoiceNumber updates from Manage Invoice page", "Status": "Fixed"},
        {"Issue": "Handled TikTok settlement — order and refund in same line", "Status": "Fixed"},
        {"Issue": "Fixed reconciliation flow with customized field mappings", "Status": "Fixed"},
    ]

    finops_df = pd.DataFrame(finops_issues)

    def finops_color(val):
        if val == "Fixed":
            return "background-color: #065F46; color: white"
        return "background-color: #7F1D1D; color: white"

    open_count = len([i for i in finops_issues if i["Status"] == "Open"])
    fixed_count = len([i for i in finops_issues if i["Status"] == "Fixed"])

    fc1, fc2 = st.columns(2)
    with fc1:
        st.metric("Open", open_count, delta_color="inverse")
    with fc2:
        st.metric("Fixed", fixed_count)

    st.dataframe(
        finops_df.style.applymap(finops_color, subset=["Status"]),
        use_container_width=True, hide_index=True, height=400,
    )
