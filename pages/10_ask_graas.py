"""Ask Graas — AI Chat Interface for the Command Center."""

import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

_env_path = str(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(_env_path, override=True)

st.set_page_config(page_title="Ask Graas | Command Center", page_icon="💬", layout="wide")
st.markdown("## 💬 Ask Graas")
st.caption("Ask anything about your business — Finance, AR, Pipeline, Product Usage, Health Scores")

# ── Check API Key ────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    st.warning("Add your Anthropic API key to `.env` as `ANTHROPIC_API_KEY=sk-ant-...` to enable the chat.")
    st.code("# In your .env file:\nANTHROPIC_API_KEY=sk-ant-api03-xxxxx", language="bash")
    st.stop()

# ── Data Loaders ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def load_all_data():
    """Load and summarise data from all tabs for context."""
    summaries = {}

    # ── Finance P&L ──────────────────────────────────────────────────
    try:
        import re

        def parse_money(s):
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

        csv_path = Path.home() / "Downloads" / "Graas FY 2026 Actuals.xlsx - Summary.csv"
        if csv_path.exists():
            raw = pd.read_csv(csv_path, header=None)
            MONTHS = ["Jan", "Feb", "Mar"]
            MONTH_COLS_ACT = {0: 3, 1: 4, 2: 5}
            MONTH_COLS_AOP = {0: 23, 1: 24, 2: 25}

            PNL_ROWS = {
                ("GMV", "Total"): 3, ("GMV", "ABU"): 4, ("GMV", "Marketplace"): 7,
                ("GMV", "EBU"): 10, ("GMV", "Platform"): 13,
                ("Net Rev", "Total"): 33, ("Net Rev", "ABU"): 34, ("Net Rev", "Marketplace"): 37,
                ("Net Rev", "EBU"): 40, ("Net Rev", "Platform"): 43,
                ("GP", "Total"): 63, ("GP", "ABU"): 64, ("GP", "Marketplace"): 67,
                ("GP", "EBU"): 70, ("GP", "Platform"): 73,
                ("OpEx", "Total"): 85,
                ("EBITDA", "Total"): 117,
                ("CoS", "Total"): 49,
            }

            pnl_data = {}
            for (metric, bu), row_idx in PNL_ROWS.items():
                if row_idx < len(raw):
                    row = raw.iloc[row_idx]
                    actuals = {m: parse_money(row.iloc[MONTH_COLS_ACT[i]]) for i, m in enumerate(MONTHS)}
                    aop = {m: parse_money(row.iloc[MONTH_COLS_AOP[i]]) for i, m in enumerate(MONTHS)}
                    pnl_data[f"{metric}_{bu}"] = {
                        "actuals": actuals,
                        "aop": aop,
                        "ytd_actual": sum(v for v in actuals.values() if v != 0),
                        "ytd_aop": sum(aop.values()),
                    }
            summaries["finance_pnl"] = pnl_data
    except Exception as e:
        summaries["finance_pnl"] = f"Error loading: {e}"

    # ── AR Data ──────────────────────────────────────────────────────
    try:
        from services.sheets_client import fetch_ar_by_bu
        ar_raw = fetch_ar_by_bu()
        if not ar_raw.empty:
            def parse_ar(s):
                s = str(s).strip()
                if s in ("", "-", "–", "—"): return 0.0
                s = s.replace(",", "").replace("$", "")
                try: return float(s)
                except: return 0.0

            customers = []
            for i in range(6, len(ar_raw)):
                row = ar_raw.iloc[i]
                bu = str(row.iloc[0]).strip()
                region = str(row.iloc[1]).strip()
                customer = str(row.iloc[2]).strip()
                if not bu or bu == "Business Unit": continue
                net = parse_ar(row.iloc[10]) if len(row) > 10 else 0
                overdue = parse_ar(row.iloc[6]) if len(row) > 6 else 0
                bad_debt = parse_ar(row.iloc[9]) if len(row) > 9 else 0
                if net != 0:
                    customers.append({
                        "customer": customer, "bu": bu, "region": region or "India",
                        "net_ar": net, "overdue_180": overdue, "bad_debt": bad_debt,
                    })
            # Summarise
            ar_df = pd.DataFrame(customers)
            summaries["ar"] = {
                "total_ar": ar_df["net_ar"].sum(),
                "india_ar": ar_df[ar_df["region"] == "India"]["net_ar"].sum(),
                "sea_ar": ar_df[ar_df["region"] == "SEA"]["net_ar"].sum(),
                "total_overdue_180": ar_df["overdue_180"].sum(),
                "total_bad_debt": ar_df["bad_debt"].sum(),
                "customer_count": len(ar_df),
                "top_10": ar_df.nlargest(10, "net_ar")[["customer", "bu", "region", "net_ar", "overdue_180"]].to_dict("records"),
            }
    except Exception as e:
        summaries["ar"] = f"Error loading: {e}"

    # ── Hoppr ────────────────────────────────────────────────────────
    try:
        from services.sheets_client import fetch_sheet_tab
        hoppr_id = os.getenv("HOPPR_SHEET_ID", "")
        if hoppr_id:
            df = fetch_sheet_tab(hoppr_id, "Hoppr__Anaysis")
            if not df.empty:
                summaries["hoppr"] = {
                    "rows": len(df),
                    "columns": list(df.columns)[:15],
                    "sample": df.head(5).to_dict("records"),
                }

        # Daily analytics
        daily_df = fetch_sheet_tab(hoppr_id, "Daily Analytics - Rohan") if hoppr_id else pd.DataFrame()
        if not daily_df.empty:
            summaries["hoppr_daily"] = {
                "rows": len(daily_df),
                "columns": list(daily_df.columns)[:15],
                "sample": daily_df.head(3).to_dict("records"),
            }
    except Exception as e:
        summaries["hoppr"] = f"Error loading: {e}"

    # ── Turbo ────────────────────────────────────────────────────────
    try:
        from services.sheets_client import fetch_turbo_health_scores
        turbo_df = fetch_turbo_health_scores()
        if not turbo_df.empty:
            summaries["turbo"] = {
                "total_accounts": len(turbo_df),
                "columns": list(turbo_df.columns)[:15],
                "sample": turbo_df.head(5).to_dict("records"),
            }
    except Exception as e:
        summaries["turbo"] = f"Error loading: {e}"

    # ── All-e Pipeline ───────────────────────────────────────────────
    try:
        from services.sheets_client import fetch_alle_active_presales
        alle_df = fetch_alle_active_presales()
        if not alle_df.empty:
            summaries["alle_pipeline"] = {
                "total_leads": len(alle_df),
                "columns": list(alle_df.columns)[:15],
                "sample": alle_df.head(10).to_dict("records"),
            }
    except Exception as e:
        summaries["alle_pipeline"] = f"Error loading: {e}"

    # ── Meeting Notes (from Slack / Granola) ─────────────────────────
    try:
        from services.notes_store import get_all_notes
        notes = get_all_notes()
        if notes:
            summaries["meeting_notes"] = [
                {
                    "client": n.get("client", ""),
                    "date": n.get("date", ""),
                    "author": n.get("author", ""),
                    "channel": n.get("channel", ""),
                    "summary": n.get("summary", ""),
                    "takeaways": n.get("takeaways", []),
                    "has_granola": bool(n.get("granola")),
                    "source": n.get("source", ""),
                }
                for n in notes[:30]  # last 30 notes
            ]
    except Exception:
        pass

    # ── Slack live notes (if no stored notes) ────────────────────────
    if "meeting_notes" not in summaries:
        try:
            from services.slack_notes import fetch_meeting_notes
            slack_notes = fetch_meeting_notes(lookback_days=30)
            if slack_notes:
                summaries["meeting_notes"] = [
                    {
                        "client": n.get("client", ""),
                        "date": n.get("date", ""),
                        "author": n.get("author", ""),
                        "channel": n.get("channel", ""),
                        "summary": n.get("summary", ""),
                        "takeaways": n.get("takeaways", []),
                        "has_granola": bool(n.get("granola")),
                        "source": "slack",
                    }
                    for n in slack_notes[:30]
                ]
        except Exception:
            pass

    return summaries


def build_system_prompt(data):
    """Build system prompt with current data context."""
    today = datetime.now().strftime("%B %d, %Y")

    # Format data context
    context_parts = []

    if "finance_pnl" in data and isinstance(data["finance_pnl"], dict):
        pnl = data["finance_pnl"]
        context_parts.append("=== FINANCE P&L (FY 2026) === [Source: Finance P&L Sheet]")
        for key, vals in pnl.items():
            if isinstance(vals, dict):
                act = vals.get("ytd_actual", 0)
                aop = vals.get("ytd_aop", 0)
                monthly = vals.get("actuals", {})
                context_parts.append(
                    f"{key}: YTD Actual=${act:,.0f}, YTD AOP=${aop:,.0f}, "
                    f"Monthly={json.dumps({m: f'${v:,.0f}' for m, v in monthly.items()})}"
                )

    if "ar" in data and isinstance(data["ar"], dict):
        ar = data["ar"]
        context_parts.append("\n=== ACCOUNTS RECEIVABLE === [Source: AR Sheet]")
        context_parts.append(f"Total Net AR: ${ar['total_ar']:,.0f}")
        context_parts.append(f"India AR: ${ar['india_ar']:,.0f}")
        context_parts.append(f"SEA AR: ${ar['sea_ar']:,.0f}")
        context_parts.append(f"Overdue >180d: ${ar['total_overdue_180']:,.0f}")
        context_parts.append(f"Bad Debt Provision: ${ar['total_bad_debt']:,.0f}")
        context_parts.append(f"Active Customers: {ar['customer_count']}")
        context_parts.append("Top 10 by Net AR:")
        for c in ar.get("top_10", []):
            context_parts.append(
                f"  - {c['customer']} ({c['bu']}, {c['region']}): "
                f"AR=${c['net_ar']:,.0f}, Overdue=${c['overdue_180']:,.0f}"
            )

    if "hoppr" in data and isinstance(data["hoppr"], dict):
        context_parts.append(f"\n=== HOPPR (AI Analytics) === [Source: Hoppr Dashboard Sheet]")
        context_parts.append(f"Total rows: {data['hoppr']['rows']}")
        context_parts.append(f"Columns: {data['hoppr']['columns']}")

    if "hoppr_daily" in data and isinstance(data["hoppr_daily"], dict):
        context_parts.append(f"\n=== HOPPR DAILY ANALYTICS === [Source: Hoppr Daily Analytics Sheet]")
        context_parts.append(f"Active sellers tracked: {data['hoppr_daily']['rows']}")
        context_parts.append(f"Columns: {data['hoppr_daily']['columns']}")
        context_parts.append(f"Sample rows: {json.dumps(data['hoppr_daily']['sample'][:2], default=str)}")

    if "turbo" in data and isinstance(data["turbo"], dict):
        context_parts.append(f"\n=== TURBO (Usage Health Scores) === [Source: Turbo Health Score Sheet]")
        context_parts.append(f"Total accounts: {data['turbo']['total_accounts']}")
        context_parts.append(f"Columns: {data['turbo']['columns']}")
        context_parts.append(f"Sample: {json.dumps(data['turbo']['sample'][:2], default=str)}")

    if "alle_pipeline" in data and isinstance(data["alle_pipeline"], dict):
        context_parts.append(f"\n=== ALL-E PRESALES PIPELINE === [Source: Presales Tracker Sheet]")
        context_parts.append(f"Total active leads: {data['alle_pipeline']['total_leads']}")
        context_parts.append(f"Columns: {data['alle_pipeline']['columns']}")
        context_parts.append(f"Sample: {json.dumps(data['alle_pipeline']['sample'], default=str)}")

    if "meeting_notes" in data and isinstance(data["meeting_notes"], list):
        context_parts.append(f"\n=== MEETING NOTES ({len(data['meeting_notes'])} recent) === [Source: Slack GTM channels / Granola]")
        for note in data["meeting_notes"]:
            source_tag = "Granola notes" if note.get("has_granola") else "Slack message only (no Granola)"
            parts = [f"  Client: {note['client']} | Date: {note['date']} | By: {note['author']} | Channel: {note['channel']} | Source: {source_tag}"]
            if note.get("summary"):
                parts.append(f"    Summary: {note['summary'][:300]}")
            if note.get("takeaways"):
                parts.append(f"    Takeaways: {'; '.join(note['takeaways'][:5])}")
            context_parts.append("\n".join(parts))

    data_context = "\n".join(context_parts)

    return f"""You are the Graas Command Center AI assistant. Today is {today}.
You help the CEO and leadership team understand business performance across all functions.

You have access to the following live data from the Graas Command Center:

{data_context}

RULES:
- Be concise and direct. The user is the CEO — don't over-explain.
- Use dollar amounts formatted with $ and commas.
- When comparing actuals vs AOP, highlight variance and whether it's good or bad.
- For AR, note concentration risk and overdue amounts.
- If data is missing for a question, say so clearly.
- Use bullet points and bold for readability.
- GP (Gross Profit) is more important than Revenue to this CEO.
- BUs are: ABU, EBU, Marketplace, Platform.
- Regions: India and SEA.
- When asked for a "board summary" or "brief", structure it as: GP, Revenue, EBITDA, AR, Pipeline.
- **ALWAYS cite your source** for every claim. Use the [Source: ...] tags from the data sections above. For example: "Nerolac is at TOF stage *(Presales Tracker Sheet)* with a deep-dive meeting scheduled *(Slack GTM / Granola notes, 14 Apr)*". This lets the reader verify the information.
- When referencing meeting notes, mention the date, who posted them, and whether Granola notes exist.
"""


# ── Chat Interface ───────────────────────────────────────────────────────────

# Load data
all_data = load_all_data()

# Show data status
with st.expander("Data Sources Status", expanded=False):
    for source, data in all_data.items():
        if isinstance(data, str) and "Error" in data:
            st.error(f"**{source}**: {data}")
        elif isinstance(data, dict):
            st.success(f"**{source}**: Loaded")
        else:
            st.warning(f"**{source}**: No data")

# Example prompts
st.markdown("**Try asking:**")
prompt_cols = st.columns(4)
example_prompts = [
    "Summarise our financial position for the board",
    "Which BU has the best GP margin?",
    "Who are our top 5 AR risks?",
    "How is the All-e pipeline looking?",
]

# Handle example prompt clicks
for i, prompt in enumerate(example_prompts):
    with prompt_cols[i]:
        if st.button(prompt, key=f"example_{i}", use_container_width=True):
            st.session_state["prefill_prompt"] = prompt

st.markdown("---")

# Initialize chat history
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Display chat history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
user_input = st.chat_input("Ask anything about your business...")

# Check for prefilled prompt
if "prefill_prompt" in st.session_state:
    user_input = st.session_state.pop("prefill_prompt")

if user_input:
    # Add user message
    st.session_state.chat_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

                system_prompt = build_system_prompt(all_data)

                # Build messages (keep last 20 for context)
                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_messages[-20:]
                ]

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2048,
                    system=system_prompt,
                    messages=messages,
                )

                assistant_msg = response.content[0].text
                st.markdown(assistant_msg)

                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": assistant_msg}
                )

            except Exception as e:
                if "authentication" in str(e).lower() or "AuthenticationError" in type(e).__name__:
                    st.error("Invalid API key. Check your `ANTHROPIC_API_KEY` in `.env`.")
                else:
                    st.error(f"Error: {e}")

# Sidebar controls
with st.sidebar:
    if st.button("Clear Chat"):
        st.session_state.chat_messages = []
        st.rerun()
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()
