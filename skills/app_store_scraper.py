"""Scrape Apple App Store reviews via iTunes Store internal API — free, no key needed."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import requests

from skills.base_skill import BaseSkill

# 10 reviews per page
PAGE_SIZE = 10

HEADERS = {
    "X-Apple-Store-Front": "143441-1,32",
    "User-Agent": "iTunes/12.0 (Macintosh; OS X 10.10)",
    "Accept": "application/json",
}

REVIEW_URL = (
    "https://itunes.apple.com/WebObjects/MZStore.woa/wa/userReviewsRow"
    "?id={app_id}&displayable-kind=11&startIndex={start}&endIndex={end}&sort=4"
)


def parse_app_store_input(value: str) -> Tuple[str, str, str]:
    value = value.strip().rstrip("#productRatings").strip()
    if value.startswith("http"):
        m_id = re.search(r"/id(\d+)", value)
        if not m_id:
            raise ValueError(f"Cannot find numeric ID in URL: {value}")
        numeric_id = m_id.group(1)
        m_country = re.search(r"apple\.com/([a-z]{2})/app/", value)
        country = m_country.group(1) if m_country else "us"
        return f"https://apps.apple.com/{country}/app/id{numeric_id}", numeric_id, country
    if value.isdigit():
        return f"https://apps.apple.com/us/app/id{value}", value, "us"
    raise ValueError(f"Unrecognised app identifier: '{value}'")


class AppStoreScraperSkill(BaseSkill):
    """Fetch App Store reviews using iTunes Store internal API (free, no key needed)."""

    @property
    def name(self) -> str:
        return "scrape_app_store_reviews"

    @property
    def description(self) -> str:
        return "Scrape App Store reviews using iTunes internal API. Free, no API key needed."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "Numeric App Store ID or full App Store URL"},
                "max_reviews": {"type": "integer", "description": "Max reviews per call (default 10)"},
                "page": {"type": "integer", "description": "Page number for pagination (default 1)"},
            },
            "required": ["app_id"],
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        raw_input: str = kwargs["app_id"].strip()
        page: int = int(kwargs.get("page", 1))
        max_reviews: int = int(kwargs.get("max_reviews", PAGE_SIZE))

        try:
            canonical_url, numeric_id, country = parse_app_store_input(raw_input)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE - 1

        print(f"   🍎 iTunes API — app {numeric_id}, page {page} (reviews {start+1}–{end+1})")

        try:
            reviews = self._fetch_page(numeric_id, start, end)
            print(f"   ✅ Got {len(reviews)} reviews")
            return {
                "success": True,
                "data": {
                    "app_id": numeric_id,
                    "app_url": canonical_url,
                    "review_count": len(reviews),
                    "page": page,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "reviews": reviews,
                },
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _fetch_page(self, app_id: str, start: int, end: int) -> List[Dict[str, Any]]:
        url = REVIEW_URL.format(app_id=app_id, start=start, end=end)
        print(f"   🌐 {url}")
        resp = requests.get(url, headers=HEADERS, timeout=30)
        print(f"   📬 Status: {resp.status_code}")
        resp.raise_for_status()

        data = resp.json()
        raw_reviews = data.get("userReviewList", [])

        reviews = []
        for r in raw_reviews:
            text = r.get("body", "").strip()
            if not text:
                continue
            reviews.append({
                "id": str(r.get("userReviewId", "")),
                "text": text,
                "title": r.get("title", ""),
                "rating": r.get("rating"),
                "author": r.get("name", "Anonymous"),
                "date": r.get("date", ""),
                "app_id": app_id,
            })
        return reviews
