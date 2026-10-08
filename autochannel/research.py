"""Demand signals from YouTube and an independent factual research excerpt.

Public search results are inspiration signals, NEVER a script to paraphrase.
Requires a YouTube Data API key. Does not scrape/download competitors' videos.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from math import log1p
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json


YOUTUBE_API = "https://www.googleapis.com/youtube/v3/"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


def get_json(url: str, params: dict) -> dict:
    request = Request(url + "?" + urlencode(params), headers={"User-Agent": "GoogleSolnsResearchBot/0.1 (educational video planning)"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def yt(api_key: str, endpoint: str, **params) -> dict:
    return get_json(YOUTUBE_API + endpoint, {"key": api_key, **params})


def channel_titles(api_key: str, channel_id: str, limit: int = 45) -> list[str]:
    """Read recent public uploads for topic deduplication, not privileged analytics."""
    result = yt(api_key, "channels", part="contentDetails", id=channel_id)
    items = result.get("items", [])
    if not items:
        raise ValueError("YouTube channel not found; check channel_id")
    playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    videos = yt(api_key, "playlistItems", part="snippet", playlistId=playlist,
                maxResults=min(limit, 50)).get("items", [])
    return [v["snippet"]["title"] for v in videos
            if v.get("snippet", {}).get("title") not in ("Private video", "Deleted video")]


def search_videos(api_key: str, phrase: str, days: int = 90) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    response = yt(api_key, "search", part="id,snippet", q=phrase, type="video",
                  maxResults=15, order="relevance", publishedAfter=cutoff,
                  safeSearch="moderate")
    snippets = response.get("items", [])
    ids = [v["id"]["videoId"] for v in snippets if v.get("id", {}).get("videoId")]
    if not ids:
        return []
    stats = yt(api_key, "videos", part="statistics", id=",".join(ids))
    views = {v["id"]: int(v.get("statistics", {}).get("viewCount", 0))
             for v in stats.get("items", [])}
    now = datetime.now(timezone.utc)
    videos = []
    for v in snippets:
        video_id = v.get("id", {}).get("videoId")
        if video_id not in views:
            continue
        snippet = v["snippet"]
        uploaded = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
        age = max(1, (now - uploaded).days)
        videos.append({
            "title": snippet["title"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "views": views[video_id],
            "days_old": age,
            "views_per_day": round(views[video_id] / age, 1),
        })
    return videos


def topic_score(seed: str, signals: list[dict], existing_titles: list[str]) -> float:
    if not signals:
        return -1
    # Logarithmic scaling prevents one viral outlier from dominating.
    velocities = sorted((v["views_per_day"] for v in signals), reverse=True)[:5]
    demand = sum(log1p(v) for v in velocities) / len(velocities)
    novelty = max((SequenceMatcher(None, seed.lower(), title.lower()).ratio()
                   for title in existing_titles), default=0)
    return round(demand * (1 - 0.85 * novelty), 3)


def rank_topics(api_key: str, channel_id: str, seeds: list[str],
                max_topics: int = 3) -> list[dict]:
    existing = channel_titles(api_key, channel_id)
    results = []
    for seed in seeds:
        signals = search_videos(api_key, seed + " explained")
        score = topic_score(seed, signals, existing)
        if score >= 0:
            results.append({"topic": seed, "score": score,
                            "signals": sorted(signals, key=lambda x: x["views_per_day"],
                                              reverse=True)[:5]})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:max_topics]


def research_reference(topic: str) -> dict:
    """An independently retrieved overview to ground basic factual claims.

    Encyclopedic summaries cannot verify every derivation; the QA stage must
    still flag equations and unsupported statements for review.
    """
    result = get_json(WIKIPEDIA_API, {
        "action": "query", "generator": "search", "gsrsearch": topic, "gsrlimit": 3,
        "prop": "extracts|info", "exintro": "1", "explaintext": "1", "inprop": "url",
        "format": "json", "formatversion": "2",
    })
    pages = result.get("query", {}).get("pages", [])
    pages = [p for p in pages if p.get("extract") and p.get("fullurl")]
    if not pages:
        raise RuntimeError(f"No independent research reference found for {topic!r}")
    page = pages[0]
    return {"title": page["title"], "url": page["fullurl"],
            "excerpt": page["extract"][:5000]}
