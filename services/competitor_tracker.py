"""Competitor monitoring via RSS feeds and news scraping."""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import feedparser
import requests
from bs4 import BeautifulSoup
import yaml

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict:
    """Load competitor config."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {"competitors": [], "alert_keywords": []}


def _cache_path(name: str) -> Path:
    key = hashlib.md5(name.encode()).hexdigest()
    return CACHE_DIR / f"competitor_{key}.json"


def _read_cache(name: str, max_age_hours: int = 4) -> Optional[List[Dict]]:
    path = _cache_path(name)
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
        if datetime.now() - cached_at < timedelta(hours=max_age_hours):
            return data.get("items", [])
    return None


def _write_cache(name: str, items: List[Dict]):
    path = _cache_path(name)
    with open(path, "w") as f:
        json.dump({
            "name": name,
            "cached_at": datetime.now().isoformat(),
            "items": items,
        }, f, indent=2, default=str)


def fetch_google_news(query: str, max_items: int = 10) -> List[Dict]:
    """Fetch news from Google News RSS."""
    url = f"https://news.google.com/rss/search?q={query}&hl=en"
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": entry.get("source", {}).get("title", "Google News"),
                "summary": entry.get("summary", "")[:200],
            })
        return items
    except Exception as e:
        return [{"title": f"Error fetching news: {e}", "link": "", "published": "", "source": "Error", "summary": ""}]


def fetch_nitter_rss(username: str, max_items: int = 10) -> List[Dict]:
    """Fetch tweets via Nitter RSS (or alternative)."""
    # Try multiple Nitter instances
    nitter_instances = [
        f"https://nitter.net/{username}/rss",
        f"https://nitter.privacydev.net/{username}/rss",
    ]

    for url in nitter_instances:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                items = []
                for entry in feed.entries[:max_items]:
                    items.append({
                        "title": entry.get("title", "")[:200],
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": f"Twitter/@{username}",
                        "summary": entry.get("description", "")[:200],
                    })
                return items
        except Exception:
            continue

    # Fallback: search Google News for Twitter posts
    return fetch_google_news(f"{username} site:twitter.com OR site:x.com", max_items=5)


def fetch_competitor_news(competitor: Dict, force_refresh: bool = False) -> List[Dict]:
    """Fetch all news for a single competitor."""
    name = competitor["name"]

    if not force_refresh:
        cached = _read_cache(name)
        if cached is not None:
            return cached

    all_items = []

    # Google News
    for keyword in competitor.get("keywords", [name.lower()]):
        items = fetch_google_news(keyword, max_items=5)
        for item in items:
            item["competitor"] = name
            item["relevant_to"] = ", ".join(competitor.get("relevant_to", []))
            item["channel"] = "News"
        all_items.extend(items)

    # Twitter via Nitter
    twitter = competitor.get("twitter", "")
    if twitter:
        tweets = fetch_nitter_rss(twitter, max_items=5)
        for item in tweets:
            item["competitor"] = name
            item["relevant_to"] = ", ".join(competitor.get("relevant_to", []))
            item["channel"] = "Twitter"
        all_items.extend(tweets)

    # LinkedIn via Google News
    linkedin = competitor.get("linkedin", "")
    if linkedin:
        li_items = fetch_google_news(f"{name} site:linkedin.com", max_items=3)
        for item in li_items:
            item["competitor"] = name
            item["relevant_to"] = ", ".join(competitor.get("relevant_to", []))
            item["channel"] = "LinkedIn"
        all_items.extend(li_items)

    # Deduplicate by title
    seen = set()
    unique_items = []
    for item in all_items:
        title_key = item["title"][:50].lower()
        if title_key not in seen:
            seen.add(title_key)
            unique_items.append(item)

    _write_cache(name, unique_items)
    return unique_items


def fetch_all_competitors(force_refresh: bool = False) -> List[Dict]:
    """Fetch news for all competitors."""
    config = load_config()
    all_items = []

    for competitor in config.get("competitors", []):
        items = fetch_competitor_news(competitor, force_refresh)
        all_items.extend(items)

    # Sort by published date (most recent first)
    all_items.sort(key=lambda x: x.get("published", ""), reverse=True)
    return all_items


def check_alerts(items: List[Dict]) -> List[Dict]:
    """Check items against alert keywords."""
    config = load_config()
    alert_keywords = config.get("alert_keywords", [])

    alerts = []
    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        matched_keywords = [kw for kw in alert_keywords if kw.lower() in text]
        if matched_keywords:
            item["alert_keywords"] = matched_keywords
            alerts.append(item)

    return alerts
