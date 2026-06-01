"""Sentiment and theme analysis of app reviews using an LLM."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from llm_client import create_llm_client, parse_json_response
from skills.base_skill import BaseSkill

load_dotenv()


class AnalyzerSkill(BaseSkill):
    """Analyze review sentiment, pain points, and praised features."""

    @property
    def name(self) -> str:
        return "analyze_sentiment"

    @property
    def description(self) -> str:
        return (
            "Analyze sentiment of Play Store reviews for one app. "
            "Returns positive/negative/neutral percentages, pain points, "
            "liked features, and an executive summary."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Display name of the app, e.g. Wealthfront",
                },
                "reviews": {
                    "type": "array",
                    "description": "List of review objects with text, rating, and author",
                },
            },
            "required": ["app_name", "reviews"],
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        app_name = kwargs["app_name"].strip()
        reviews: List[Dict[str, Any]] = kwargs["reviews"]

        if not app_name:
            return {"success": False, "error": "app_name cannot be empty"}

        if not reviews:
            return {
                "success": False,
                "error": f"No reviews provided for {app_name}",
            }

        provider = os.getenv("LLM_PROVIDER", "gemini")
        print(
            f"🧠 Analyzing {len(reviews)} reviews for {app_name} "
            f"via {provider.upper()}..."
        )

        try:
            client = create_llm_client(provider)
            sample = self._prepare_review_sample(reviews)
            system_prompt = (
                "You are a competitive intelligence analyst specializing in "
                "mobile fintech and investing apps. Respond with valid JSON only."
            )
            user_prompt = self._build_analysis_prompt(app_name, sample)

            raw = client.complete(system_prompt, user_prompt)
            parsed = parse_json_response(raw)
            result = self._normalize_analysis(parsed, app_name, len(reviews))

            print(f"✅ Sentiment analysis complete for {app_name}")
            return {"success": True, "data": result}

        except ValueError as exc:
            print(f"❌ JSON parse error for {app_name}: {exc}")
            return {"success": False, "error": f"Failed to parse LLM JSON: {exc}"}
        except Exception as exc:
            print(f"❌ Analysis failed for {app_name}: {exc}")
            return {"success": False, "error": str(exc)}

    def _prepare_review_sample(
        self, reviews: List[Dict[str, Any]], limit: int = 40
    ) -> List[Dict[str, Any]]:
        """Trim reviews for token limits while keeping rating diversity."""
        if len(reviews) <= limit:
            return reviews

        by_rating: Dict[int, List[Dict[str, Any]]] = {}
        for review in reviews:
            rating = review.get("rating") or 0
            by_rating.setdefault(int(rating), []).append(review)

        sampled: List[Dict[str, Any]] = []
        per_bucket = max(1, limit // max(len(by_rating), 1))
        for bucket in by_rating.values():
            sampled.extend(bucket[:per_bucket])
        return sampled[:limit]

    def _build_analysis_prompt(
        self, app_name: str, reviews: List[Dict[str, Any]]
    ) -> str:
        compact = [
            {
                "text": (r.get("text") or "")[:500],
                "rating": r.get("rating"),
                "author": r.get("author", "Anonymous"),
            }
            for r in reviews
        ]
        return f"""Analyze these Google Play reviews for "{app_name}".

Reviews (JSON):
{json.dumps(compact, ensure_ascii=False)}

Return ONLY a JSON object with this exact structure:
{{
  "app_name": "{app_name}",
  "sentiment_percentages": {{
    "positive": <number 0-100>,
    "negative": <number 0-100>,
    "neutral": <number 0-100>
  }},
  "pain_points": ["<specific user complaint>", "..."],
  "features_liked": ["<praised feature>", "..."],
  "summary": "<2-3 sentence executive summary>"
}}

Rules:
- sentiment_percentages must sum to approximately 100
- base percentages on review content, not star ratings alone
- pain_points and features_liked must be specific and actionable
"""

    def _normalize_analysis(
        self, parsed: Dict[str, Any], app_name: str, review_count: int
    ) -> Dict[str, Any]:
        """Ensure required fields exist with sane defaults."""
        sentiment = parsed.get("sentiment_percentages") or parsed.get("sentiment") or {}
        return {
            "app_name": parsed.get("app_name", app_name),
            "review_count": review_count,
            "sentiment_percentages": {
                "positive": float(sentiment.get("positive", 0)),
                "negative": float(sentiment.get("negative", 0)),
                "neutral": float(sentiment.get("neutral", 0)),
            },
            "pain_points": list(parsed.get("pain_points") or []),
            "features_liked": list(
                parsed.get("features_liked") or parsed.get("features") or []
            ),
            "summary": parsed.get("summary", ""),
        }
