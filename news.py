"""
Football news fetcher for PULSE90 from BBC Sport public RSS feed.
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
import time

FEED_URL = "http://feeds.bbci.co.uk/sport/football/rss.xml"
USER_AGENT = "PULSE90/2.0 (+https://example.com) football-highlight-app"

_CACHE = {
    "timestamp": 0,
    "items": []
}
CACHE_TTL = 900  # 15 minutes

FALLBACK_NEWS = [
    {
        "title": "Champions League dramatic finishes: High-intensity moments captured",
        "link": "https://www.bbc.com/sport/football",
        "source": "BBC Sport",
        "summary": "Epic crowd roars and last-minute winners light up the European nights.",
        "category": "Champions League"
    },
    {
        "title": "Premier League title race heats up with sensational stoppage-time stunner",
        "link": "https://www.bbc.com/sport/football",
        "source": "BBC Sport",
        "summary": "Electric stadium atmosphere as late drama reshapes the top of the table.",
        "category": "Premier League"
    },
    {
        "title": "World Cup Qualifiers: Decibels soar as underdogs clinch qualification",
        "link": "https://www.bbc.com/sport/football",
        "source": "BBC Sport",
        "summary": "Historic scenes from packed stadiums across the globe celebrating glory.",
        "category": "International"
    },
    {
        "title": "Tactical breakdown: How pressing triggers match the loudest crowd reactions",
        "link": "https://www.bbc.com/sport/football",
        "source": "BBC Sport",
        "summary": "Analyzing the connection between pitch momentum and arena decibel spikes.",
        "category": "Analysis"
    }
]


def fetch_football_news(limit: int = 8) -> list[dict]:
    global _CACHE
    now = time.time()
    if _CACHE["items"] and (now - _CACHE["timestamp"] < CACHE_TTL):
        return _CACHE["items"][:limit]

    try:
        request = urllib.request.Request(FEED_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()

        root = ET.fromstring(raw)
        items = root.findall("./channel/item")[:limit]

        news = []
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            summary = (item.findtext("description") or "").strip()
            category = (item.findtext("category") or "Football").strip()
            news.append({
                "title": title,
                "link": link,
                "source": "BBC Sport",
                "summary": summary,
                "category": category,
            })

        if news:
            _CACHE = {"timestamp": now, "items": news}
            return news

    except Exception:
        pass

    return FALLBACK_NEWS[:limit]
