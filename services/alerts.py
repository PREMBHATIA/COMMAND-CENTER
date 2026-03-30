"""Alert system — Slack webhook notifications for Graas Command Center."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def send_slack(text: str, blocks: List[Dict] = None) -> bool:
    """Send a message to Slack via webhook."""
    if not WEBHOOK_URL:
        print("No SLACK_WEBHOOK_URL configured")
        return False
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Slack send failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# ALERT CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def check_hoppr_alerts(daily_df: pd.DataFrame) -> List[str]:
    """Check for Hoppr usage drops >50% WoW."""
    alerts = []
    if daily_df.empty or 'date' not in daily_df.columns:
        return alerts

    today = daily_df["date"].max()
    this_week = daily_df[daily_df["date"] >= today - pd.Timedelta(days=7)]
    last_week = daily_df[
        (daily_df["date"] >= today - pd.Timedelta(days=14)) &
        (daily_df["date"] < today - pd.Timedelta(days=7))
    ]

    for metric, label in [("total_queries", "Queries"), ("unique_users", "Unique Users"),
                           ("unique_sellers", "Unique Sellers")]:
        tw = this_week[metric].sum()
        lw = last_week[metric].sum()
        if lw > 0:
            change = (tw - lw) / lw * 100
            if change < -50:
                alerts.append(f"Hoppr {label} dropped {change:.0f}% WoW ({lw} → {tw})")

    return alerts


def check_turbo_alerts(trends_df: pd.DataFrame) -> List[str]:
    """Check for top-50 accounts dropping below 30."""
    alerts = []
    if trends_df.empty:
        return alerts

    top50 = trends_df.sort_values("current_score", ascending=False).head(50)
    at_risk = top50[(top50["current_score"] < 30) & (top50["at_risk"] == True)]

    if not at_risk.empty:
        names = at_risk["display_name"].head(5).tolist()
        alerts.append(
            f"Turbo: {len(at_risk)} top-50 accounts below 30 for 2+ weeks: {', '.join(names)}"
        )

    # Big decliners
    big_drops = top50[top50["change"] < -20]
    if not big_drops.empty:
        for _, row in big_drops.head(3).iterrows():
            alerts.append(
                f"Turbo: {row['display_name']} dropped {row['change']:+.0f} pts "
                f"({row['prev_score']} → {row['current_score']})"
            )

    return alerts


def check_revenue_alerts(revenue_data: dict) -> List[str]:
    """Check for quarterly achievement below 80%."""
    alerts = []
    # This would parse the revenue data structure
    # For now, placeholder until Google Sheets API is connected
    return alerts


def _get_last_email_date(contacts_str: str) -> Optional[datetime]:
    """Check Gmail for the most recent email with any of the contact domains/emails."""
    if not contacts_str or str(contacts_str) == 'nan':
        return None

    # Extract email domains from contacts
    import re
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', str(contacts_str))
    if not emails:
        return None

    # Get unique domains (excluding graas.ai)
    domains = set()
    for email in emails:
        domain = email.split('@')[1]
        if 'graas' not in domain:
            domains.add(domain)

    if not domains:
        return None

    # Search Gmail for recent emails with these domains
    try:
        from pathlib import Path
        import subprocess, json

        # Build search query: from:domain1 OR to:domain1 OR from:domain2 ...
        parts = []
        for domain in list(domains)[:2]:  # Limit to 2 domains
            parts.append(f"from:{domain}")
            parts.append(f"to:{domain}")
        query = " OR ".join(parts) + " after:2026/01/01"

        # We can't call Gmail MCP from here, so return None
        # This will be handled at the alert runner level
        return None
    except Exception:
        return None


def check_alle_alerts(deals_df: pd.DataFrame, gmail_last_contact: Dict[str, str] = None) -> List[str]:
    """Check All-e pipeline for actionable alerts.

    Args:
        deals_df: DataFrame of deals
        gmail_last_contact: Optional dict of {lead_name: last_email_date_iso} from Gmail cross-check
    """
    alerts = []
    if deals_df.empty or 'status' not in deals_df.columns:
        return alerts

    gmail_last_contact = gmail_last_contact or {}

    # ── Proposals needing a chaser ────────────────────────────────────────────
    proposals = deals_df[deals_df['status'] == '3-Proposal sent']
    if 'days_since_contact' in deals_df.columns:
        for _, deal in proposals.iterrows():
            lead = deal['lead_name']
            sheet_days = int(deal['days_since_contact']) if pd.notna(deal['days_since_contact']) else 0

            # If we have Gmail data, use that instead of sheet date
            if lead in gmail_last_contact:
                gmail_date = gmail_last_contact[lead]
                if gmail_date:
                    gmail_days = (datetime.now() - datetime.fromisoformat(gmail_date)).days
                    actual_days = gmail_days
                else:
                    actual_days = sheet_days
            else:
                actual_days = sheet_days

            if actual_days > 14:
                alerts.append(
                    f"All-e: *{lead}* — proposal sent, needs chaser ({actual_days} days since last email)"
                )

    return alerts


def check_competitor_alerts(items: List[Dict], alert_keywords: List[str]) -> List[str]:
    """Check competitor news against alert keywords."""
    alerts = []
    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        matched = [kw for kw in alert_keywords if kw.lower() in text]
        if matched:
            alerts.append(
                f"Competitor: {item['competitor']} — {item.get('title', '')[:100]} "
                f"(keywords: {', '.join(matched)})"
            )
    return alerts


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ALERT RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_all_alerts():
    """Run all alert checks and send to Slack."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.data_processor import process_hoppr_daily, process_turbo_health, compute_turbo_trends
    from services.competitor_tracker import fetch_all_competitors, load_config

    all_alerts = []

    # ── Hoppr ─────────────────────────────────────────────────────────────────
    try:
        hoppr_csv = Path.home() / "Downloads" / "hoppr Dashboard - Hoppr__Anaysis.csv"
        if hoppr_csv.exists():
            raw = pd.read_csv(hoppr_csv)
            daily = process_hoppr_daily(raw)
            all_alerts.extend(check_hoppr_alerts(daily))
    except Exception as e:
        print(f"Hoppr alert check failed: {e}")

    # ── Turbo ─────────────────────────────────────────────────────────────────
    try:
        turbo_csv = Path.home() / "Downloads" / "Pvt Beta Consolidated Insights - Usage Health Score.csv"
        if turbo_csv.exists():
            raw = pd.read_csv(turbo_csv, header=1)
            health = process_turbo_health(raw)
            trends = compute_turbo_trends(health)
            all_alerts.extend(check_turbo_alerts(trends))
    except Exception as e:
        print(f"Turbo alert check failed: {e}")

    # ── All-e (with Gmail cross-check) ──────────────────────────────────────────
    try:
        alle_candidates = [
            "All-e - Foundry Presales Tracker - Active presales (1).csv",
            "All-e - Foundry Presales Tracker - Active presales.csv",
        ]
        for name in alle_candidates:
            alle_csv = Path.home() / "Downloads" / name
            if alle_csv.exists():
                deals = pd.read_csv(alle_csv)
                col_map = {}
                for col in deals.columns:
                    cl = col.strip().lower()
                    if 'lead name' in cl: col_map[col] = 'lead_name'
                    elif 'lead status' in cl: col_map[col] = 'status'
                    elif 'latest conv date' in cl: col_map[col] = 'latest_conv'
                    elif 'email' in cl: col_map[col] = 'contacts'
                deals = deals.rename(columns=col_map)
                if 'latest_conv' in deals.columns:
                    deals['latest_conv'] = pd.to_datetime(deals['latest_conv'], format='mixed', errors='coerce')
                    deals['days_since_contact'] = (pd.Timestamp.now() - deals['latest_conv']).dt.days

                # Gmail cross-check is done externally (by the scheduled task)
                # and passed as gmail_last_contact dict. When running standalone,
                # we use sheet dates as fallback.
                all_alerts.extend(check_alle_alerts(deals))
                break
    except Exception as e:
        print(f"All-e alert check failed: {e}")

    # ── Competitors ───────────────────────────────────────────────────────────
    try:
        config = load_config()
        items = fetch_all_competitors(force_refresh=True)
        alert_keywords = config.get("alert_keywords", [])
        all_alerts.extend(check_competitor_alerts(items, alert_keywords))
    except Exception as e:
        print(f"Competitor alert check failed: {e}")

    # ── Format as weekly digest ─────────────────────────────────────────────────
    if not all_alerts:
        print("No alerts to send")
        return all_alerts

    hoppr_alerts = [a for a in all_alerts if a.startswith("Hoppr")]
    turbo_alerts = [a for a in all_alerts if a.startswith("Turbo")]
    alle_alerts = [a for a in all_alerts if a.startswith("All-e")]
    comp_alerts = [a for a in all_alerts if a.startswith("Competitor")]

    lines = [
        f"🎯 *Graas Command Center — Weekly Digest*",
        f"_{datetime.now().strftime('%a %b %d, %Y')}_",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if hoppr_alerts:
        lines.append("")
        lines.append("📊 *HOPPR*")
        for a in hoppr_alerts:
            lines.append(f"• ⚠️ {a.replace('Hoppr ', '')}")

    if turbo_alerts:
        lines.append("")
        lines.append("🔧 *TURBO*")
        for a in turbo_alerts[:5]:
            lines.append(f"• ⚠️ {a.replace('Turbo: ', '')}")
        if len(turbo_alerts) > 5:
            lines.append(f"• ...and {len(turbo_alerts) - 5} more")

    if alle_alerts:
        lines.append("")
        lines.append("🤖 *ALL-E PIPELINE*")
        for a in alle_alerts:
            lines.append(f"• ⚠️ {a.replace('All-e: ', '')}")

    if comp_alerts:
        lines.append("")
        lines.append("🔍 *COMPETITOR INTEL*")
        for a in comp_alerts[:8]:
            lines.append(f"• {a.replace('Competitor: ', '')}")
        if len(comp_alerts) > 8:
            lines.append(f"• ...and {len(comp_alerts) - 8} more")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")

    digest = "\n".join(lines)
    send_slack(digest)
    print(f"Sent weekly digest with {len(all_alerts)} alerts to Slack")

    return all_alerts


if __name__ == "__main__":
    alerts = run_all_alerts()
    for a in alerts:
        print(f"  → {a}")
