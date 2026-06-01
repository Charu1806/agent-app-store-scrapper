"""Scrape Google Play Store reviews via the Apify API."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

from skills.base_skill import BaseSkill

load_dotenv()


class ScraperSkill(BaseSkill):
    """Fetch Play Store reviews for a given Android package id."""

    API_BASE = "https://api.apify.com/v2"

    @property
    def name(self) -> str:
        return "scrape_reviews"

    @property
    def description(self) -> str:
        return (
            "Scrape user reviews from Google Play Store for one app. "
            "Returns review text, star rating, and author name as JSON."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "Android package name, e.g. com.wealthfront",
                },
                "max_reviews": {
                    "type": "integer",
                    "description": "Maximum number of reviews to fetch (default 50)",
                },
            },
            "required": ["app_id"],
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        app_id = kwargs["app_id"].strip()
        max_reviews = int(kwargs.get("max_reviews", 50))

        if not app_id or "." not in app_id:
            return {
                "success": False,
                "error": f"Invalid app_id: '{app_id}'. Expected a package name like com.wealthfront",
            }

        token = os.getenv("APIFY_TOKEN")
        actor_id = os.getenv("APIFY_ACTOR_ID", "sync-network~google-play-reviews-scraper")

        if not token:
            return {
                "success": False,
                "error": "APIFY_TOKEN is not set in .env",
            }

        print(f"📱 Scraping Play Store reviews for {app_id} (max {max_reviews})...")

        try:
            raw_items = self._run_apify_actor(token, actor_id, app_id, max_reviews)
            reviews = self._normalize_reviews(raw_items, app_id)
            print(f"✅ Scraped {len(reviews)} reviews for {app_id}")
            return {
                "success": True,
                "data": {
                    "app_id": app_id,
                    "review_count": len(reviews),
                    "reviews": reviews,
                },
            }
        except requests.RequestException as exc:
            print(f"❌ Network error while scraping {app_id}: {exc}")
            return {"success": False, "error": f"Apify request failed: {exc}"}
        except Exception as exc:
            print(f"❌ Scraper failed for {app_id}: {exc}")
            return {"success": False, "error": str(exc)}

    def _run_apify_actor(
        self, token: str, actor_id: str, app_id: str, max_reviews: int
    ) -> List[Dict[str, Any]]:
        """Call Apify run-sync-get-dataset-items and return raw dataset rows."""
        actor_path = actor_id.replace("/", "~")
        url = f"{self.API_BASE}/acts/{actor_path}/run-sync-get-dataset-items"

        payload = self._build_actor_input(app_id, max_reviews)

        response = requests.post(
            url,
            params={"token": token},
            json=payload,
            timeout=300,
        )

        if response.status_code >= 400:
            raise requests.HTTPError(
                f"Apify HTTP {response.status_code}: {response.text[:500]}",
                response=response,
            )

        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        return [data] if data else []

    def _build_actor_input(self, app_id: str, max_reviews: int) -> Dict[str, Any]:
        """Support common Apify Google Play review actor input shapes."""
        return {
            "appIds": [app_id],
            "appIdsOrUrls": [app_id],
            "maxReviews": max_reviews,
            "maxReviewsPerApp": max_reviews,
            "sort": "newest",
            "sortBy": "newest",
            "language": "en",
            "country": "us",
        }

    def _normalize_reviews(
        self, items: List[Dict[str, Any]], app_id: str
    ) -> List[Dict[str, Any]]:
        """Map heterogeneous Apify output fields to a consistent review shape."""
        reviews: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            text = (
                item.get("text")
                or item.get("reviewText")
                or item.get("content")
                or item.get("body")
                or ""
            ).strip()
            if not text:
                continue
            rating = (
                item.get("score")
                or item.get("rating")
                or item.get("stars")
                or item.get("starRating")
            )
            author = (
                item.get("userName")
                or item.get("author")
                or item.get("reviewerName")
                or item.get("name")
                or "Anonymous"
            )
            try:
                rating_int = int(rating) if rating is not None else None
            except (TypeError, ValueError):
                rating_int = None

            reviews.append(
                {
                    "text": text,
                    "rating": rating_int,
                    "author": str(author),
                    "app_id": item.get("appId") or app_id,
                }
            )
        return reviews
