"""Sports news fetcher for LLM context enrichment."""

import logging
import time
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[list[str], float]] = {}
_CACHE_TTL_SECONDS = 6 * 3600  # 6 hours


def _get_sport_query(sport: str) -> str:
    sport_queries = {
        "football": "NFL fantasy football",
        "basketball": "NBA fantasy basketball",
        "baseball": "MLB fantasy baseball",
        "hockey": "NHL fantasy hockey",
    }
    return sport_queries.get(sport, f"{sport} fantasy sports")


def fetch_sports_news(sport: str) -> list[str]:
    cache_key = sport.lower()
    now = time.time()

    if cache_key in _cache:
        headlines, cached_at = _cache[cache_key]
        if now - cached_at < _CACHE_TTL_SECONDS:
            return headlines

    if not settings.news_api_key:
        return []

    try:
        from newsapi import NewsApiClient
        newsapi = NewsApiClient(api_key=settings.news_api_key)

        query = _get_sport_query(sport)
        response = newsapi.get_top_headlines(
            q=query,
            language="en",
            page_size=10,
        )

        if response.get("status") != "ok":
            logger.warning("NewsAPI returned non-ok status: %s", response.get("status"))
            return _cache.get(cache_key, ([], 0))[0]

        headlines = [
            article["title"]
            for article in response.get("articles", [])
            if article.get("title")
        ][:10]

        _cache[cache_key] = (headlines, now)
        logger.info("Fetched %d sports headlines for %s", len(headlines), sport)
        return headlines

    except Exception:
        logger.exception("Failed to fetch sports news for %s", sport)
        return _cache.get(cache_key, ([], 0))[0]
