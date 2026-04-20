"""Competitor Intelligence — Weekly Wrap."""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

_env_path = str(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(_env_path, override=True)

from services.competitor_tracker import fetch_all_competitors, check_alerts, load_config

st.set_page_config(page_title="Competitors | Graas", page_icon="🔍", layout="wide")
st.markdown("## 🔍 Competitor Intelligence — Weekly Wrap")

config = load_config()
competitor_names = [c["name"] for c in config.get("competitors", [])]
products = sorted(set(
    p for c in config.get("competitors", [])
    for p in c.get("relevant_to", [])
))
regions = sorted(set(
    c.get("region", "Unknown") for c in config.get("competitors", [])
))

# ── Controls ──────────────────────────────────────────────────────────────────

col_refresh, col_product, col_region = st.columns([1, 2, 2])

with col_refresh:
    force_refresh = st.button("🔄 Fetch Latest")
with col_product:
    selected_products = st.multiselect("Product", products, default=products)
with col_region:
    selected_regions = st.multiselect("Region", regions, default=regions)

# ── Fetch Data ────────────────────────────────────────────────────────────────

with st.spinner("Fetching competitor intelligence..."):
    all_items = fetch_all_competitors(force_refresh=force_refresh)

# Filter by product and region
selected_competitors = [
    c["name"] for c in config.get("competitors", [])
    if any(p in selected_products for p in c.get("relevant_to", []))
    and c.get("region", "Unknown") in selected_regions
]

filtered = [
    item for item in all_items
    if item.get("competitor") in selected_competitors
]

alerts = check_alerts(filtered)

# ── KPI Row ───────────────────────────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Competitors Tracked", len(selected_competitors))
with c2:
    st.metric("Items This Week", len(filtered))
with c3:
    st.metric("Alerts", len(alerts))
with c4:
    news = len([i for i in filtered if i["channel"] == "News"])
    social = len([i for i in filtered if i["channel"] in ("Twitter", "LinkedIn")])
    st.metric("News / Social", f"{news} / {social}")

# ══════════════════════════════════════════════════════════════════════════════

tab_insights, tab_wrap, tab_by_product, tab_tracker = st.tabs([
    "💡 Key Insights",
    "📰 Weekly Wrap",
    "🎯 By Product",
    "📋 Competitor Tracker",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 0: KEY INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Classification logic ─────────────────────────────────────────────────────

FUNDING_KEYWORDS = [
    "raised", "funding", "series a", "series b", "series c", "series d", "series e",
    "seed round", "venture", "valuation", "ipo", "capital", "investment round",
    "million", "billion", "$", "fundraise", "pre-seed", "growth equity",
    "investor", "led by", "backed by",
]

FEATURE_KEYWORDS = [
    "launch", "launched", "launches", "new feature", "new product", "announces",
    "introduced", "introducing", "rolls out", "release", "released", "update",
    "integration", "connector", "platform update", "now supports", "adds support",
    "expands", "partnership", "api", "sdk", "dashboard", "module",
]

AGENTIC_KEYWORDS = [
    "agent", "agentic", "ai agent", "autonomous", "workflow automation",
    "ai-powered", "copilot", "autopilot", "llm", "large language model",
    "generative ai", "gen ai", "chatbot", "conversational ai", "voice ai",
    "ai assistant", "machine learning", "orchestration", "rag",
    "natural language", "foundation model", "multimodal",
]

def classify_item(item):
    """Classify a news item into insight categories."""
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    categories = []

    funding_score = sum(1 for kw in FUNDING_KEYWORDS if kw in text)
    if funding_score >= 2:
        categories.append("funding")

    feature_score = sum(1 for kw in FEATURE_KEYWORDS if kw in text)
    if feature_score >= 1:
        categories.append("features")

    agentic_score = sum(1 for kw in AGENTIC_KEYWORDS if kw in text)
    if agentic_score >= 1:
        categories.append("agentic")

    return categories

def classify_with_llm(items):
    """Use Claude to classify ambiguous items into agentic breakthroughs."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or not items:
        return {}

    titles = []
    for i, item in enumerate(items[:30]):
        titles.append(f"{i}: [{item.get('competitor','')}] {item.get('title','')}")

    prompt = (
        "Below are news headlines about e-commerce/SaaS competitors. "
        "Identify which ones describe genuinely interesting AI/agentic breakthroughs or workflows "
        "(not just routine product updates or marketing). "
        "Return ONLY a JSON array of the line numbers that qualify. "
        "Be selective — only flag truly notable agentic developments.\n\n"
        + "\n".join(titles)
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Parse JSON array from response
        import re
        match = re.search(r'\[[\d,\s]*\]', text)
        if match:
            indices = json.loads(match.group())
            return {i: True for i in indices if isinstance(i, int)}
    except Exception:
        pass
    return {}

# Classify all items
funding_items = []
feature_items = []
agentic_items = []
unclassified = []

for item in filtered:
    cats = classify_item(item)
    if "funding" in cats:
        funding_items.append(item)
    if "features" in cats:
        feature_items.append(item)
    if "agentic" in cats:
        agentic_items.append(item)
    if not cats:
        unclassified.append(item)

# LLM pass on items not yet classified as agentic
if unclassified and os.getenv("ANTHROPIC_API_KEY"):
    llm_agentic = classify_with_llm(unclassified)
    for i, is_agentic in llm_agentic.items():
        if is_agentic and i < len(unclassified):
            agentic_items.append(unclassified[i])

with tab_insights:
    st.markdown("### Key Insights")
    st.caption("Auto-curated from competitor news — funding, features, and agentic breakthroughs")

    # ── KPI row ──────────────────────────────────────────────────────────────
    ic1, ic2, ic3, ic4 = st.columns(4)
    with ic1:
        st.metric("Total Items", len(filtered))
    with ic2:
        st.metric("Funding / Raises", len(funding_items))
    with ic3:
        st.metric("Feature Launches", len(feature_items))
    with ic4:
        st.metric("Agentic / AI", len(agentic_items))

    def render_insight_card(item, color, icon):
        comp = item.get("competitor", "")
        title = item.get("title", "")
        link = item.get("link", "")
        published = item.get("published", "")[:16]
        source = item.get("source", "")
        relevant = item.get("relevant_to", "")
        st.markdown(
            f'<div style="border-left: 3px solid {color}; padding: 8px 12px; '
            f'margin-bottom: 8px; background: #1E1E2E; border-radius: 6px;">'
            f'<div style="display: flex; justify-content: space-between; align-items: baseline;">'
            f'<span style="font-weight: 600; font-size: 0.9rem;">{icon} {comp}</span>'
            f'<span style="font-size: 0.75rem; color: #9CA3AF;">{relevant}</span>'
            f'</div>'
            f'<div style="font-size: 0.85rem; margin-top: 4px;">{title}</div>'
            f'<div style="font-size: 0.75rem; color: #6B7280; margin-top: 2px;">'
            f'{source} | {published} | <a href="{link}" style="color: #60A5FA;">Read</a></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Funding / Raises ─────────────────────────────────────────────────────
    st.markdown("#### 💰 Funding & Raises")
    if funding_items:
        for item in funding_items[:10]:
            render_insight_card(item, "#F59E0B", "💰")
    else:
        st.caption("No funding news detected this period.")

    st.markdown("")

    # ── Feature Launches ─────────────────────────────────────────────────────
    st.markdown("#### 🚀 New Platform Features")
    if feature_items:
        for item in feature_items[:10]:
            render_insight_card(item, "#3B82F6", "🚀")
    else:
        st.caption("No feature launches detected this period.")

    st.markdown("")

    # ── Agentic Breakthroughs ────────────────────────────────────────────────
    st.markdown("#### 🤖 Agentic Breakthroughs & AI Workflows")
    st.caption("Curated via keyword matching + LLM classification")
    if agentic_items:
        for item in agentic_items[:10]:
            render_insight_card(item, "#10B981", "🤖")
    else:
        st.caption("No agentic breakthroughs detected this period.")

    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: WEEKLY WRAP
# ══════════════════════════════════════════════════════════════════════════════

with tab_wrap:

    # ── Alerts first ──────────────────────────────────────────────────────────
    if alerts:
        st.markdown("### ⚠️ Key Alerts")
        for alert in alerts[:10]:
            keywords = ", ".join(alert.get("alert_keywords", []))
            st.markdown(
                f"**🚨 {alert['competitor']}** — `{keywords}`\n"
                f"> {alert['title']}\n"
                f"> {alert.get('relevant_to', '')} | {alert['channel']} | "
                f"[Read →]({alert.get('link', '')})"
            )
        st.markdown("---")

    # ── Grouped by competitor ─────────────────────────────────────────────────
    st.markdown("### This Week's Intel by Competitor")

    for comp in config.get("competitors", []):
        name = comp["name"]
        if name not in selected_competitors:
            continue

        comp_items = [i for i in filtered if i.get("competitor") == name]
        if not comp_items:
            continue

        region = comp.get("region", "")
        relevant = ", ".join(comp.get("relevant_to", []))

        with st.expander(f"**{name}** — {relevant} ({region}) — {len(comp_items)} items", expanded=len(comp_items) <= 5):
            for item in comp_items[:10]:
                channel_icon = {"News": "📰", "Twitter": "🐦", "LinkedIn": "💼"}.get(item["channel"], "📄")
                title = item.get("title", "")
                link = item.get("link", "")
                published = item.get("published", "")[:25]
                source = item.get("source", "")

                st.markdown(f"{channel_icon} **{title}**")
                st.caption(f"{source} | {published} | [Read →]({link})")

    if not filtered:
        st.info("No items found. Try fetching latest or adjusting filters.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: BY PRODUCT
# ══════════════════════════════════════════════════════════════════════════════

with tab_by_product:
    st.markdown("### Intel Grouped by Product")

    product_groups = {}
    for comp in config.get("competitors", []):
        for prod in comp.get("relevant_to", []):
            if prod not in product_groups:
                product_groups[prod] = []
            product_groups[prod].append(comp["name"])

    for product in sorted(product_groups.keys()):
        if product not in selected_products:
            continue

        comp_names = product_groups[product]
        product_items = [i for i in filtered if i.get("competitor") in comp_names]

        st.markdown(f"#### {product}")
        st.caption(f"Competitors: {', '.join(comp_names)}")

        if product_items:
            for item in product_items[:8]:
                channel_icon = {"News": "📰", "Twitter": "🐦", "LinkedIn": "💼"}.get(item["channel"], "📄")
                st.markdown(
                    f"{channel_icon} **{item['competitor']}** — {item.get('title', '')[:120]}"
                )
                st.caption(
                    f"{item.get('source', '')} | {item.get('published', '')[:25]} | "
                    f"[Read →]({item.get('link', '')})"
                )
        else:
            st.caption("No items this week.")

        st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: COMPETITOR TRACKER
# ══════════════════════════════════════════════════════════════════════════════

with tab_tracker:
    st.markdown("### Competitor Overview")

    tracker_data = []
    for comp in config.get("competitors", []):
        name = comp["name"]
        comp_items = [i for i in all_items if i.get("competitor") == name]
        comp_alerts = check_alerts(comp_items)

        twitter = comp.get("twitter", "")
        twitter_display = f"[@{twitter}](https://x.com/{twitter})" if twitter else "—"

        tracker_data.append({
            "Competitor": name,
            "Relevant To": ", ".join(comp.get("relevant_to", [])),
            "Region": comp.get("region", ""),
            "Items": len(comp_items),
            "Alerts": len(comp_alerts),
            "Twitter": twitter_display,
        })

    if tracker_data:
        st.dataframe(
            pd.DataFrame(tracker_data),
            use_container_width=True, hide_index=True,
            column_config={
                "Twitter": st.column_config.LinkColumn("Twitter", display_text="Open"),
            },
        )

    # ── Competitor landscape map ──────────────────────────────────────────────
    st.markdown("### Competitive Landscape")

    landscape = {}
    for comp in config.get("competitors", []):
        for prod in comp.get("relevant_to", []):
            if prod not in landscape:
                landscape[prod] = {"US": [], "India": [], "SE Asia": []}
            region = comp.get("region", "Other")
            if region in landscape[prod]:
                landscape[prod][region].append(comp["name"])
            else:
                if "Other" not in landscape[prod]:
                    landscape[prod]["Other"] = []
                landscape[prod]["Other"].append(comp["name"])

    for product, regions_map in sorted(landscape.items()):
        st.markdown(f"**{product}**")
        cols = st.columns(len(regions_map))
        for col, (region, names) in zip(cols, regions_map.items()):
            with col:
                st.markdown(f"*{region}*")
                for name in names:
                    st.markdown(f"- {name}")
        st.markdown("---")
