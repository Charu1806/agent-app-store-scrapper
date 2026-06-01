"""Score and rank apps against each other competitively."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from llm_client import create_llm_client, parse_json_response
from skills.base_skill import BaseSkill

load_dotenv()


class CompetitiveScorerSkill(BaseSkill):
    """Rank apps 0-100 on sentiment, features, ratings, and trends."""

    @property
    def name(self) -> str:
        return "score_competitors"

    @property
    def description(self) -> str:
        return (
            "Compare multiple apps and produce competitive scores (0-100) "
            "based on sentiment, feature coverage, ratings, and trend direction."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "analysis_data": {
                    "type": "object",
                    "description": "Dict of app_name -> analysis dict (sentiment, features, trends)",
                },
            },
            "required": ["analysis_data"],
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        analysis_data: Dict[str, Any] = kwargs["analysis_data"]

        if len(analysis_data) < 2:
            return {"success": False, "error": "Need at least 2 apps to compare"}

        # Compute numeric scores
        scored = {}
        for app_name, data in analysis_data.items():
            scored[app_name] = self._score_app(app_name, data)

        # Normalize to 0-100 relative to best in cohort
        raw_scores = {k: v["raw_score"] for k, v in scored.items()}
        max_score = max(raw_scores.values()) or 1
        for app_name in scored:
            scored[app_name]["score"] = round(
                (scored[app_name]["raw_score"] / max_score) * 100, 1
            )

        rankings = sorted(scored.values(), key=lambda x: x["score"], reverse=True)

        # LLM recommendations
        recommendations = self._generate_recommendations(rankings, analysis_data)

        return {
            "success": True,
            "data": {
                "rankings": rankings,
                "recommendations": recommendations,
                "winner": rankings[0]["app_name"] if rankings else None,
            },
        }

    def _score_app(self, app_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        sentiment = data.get("sentiment", {}) or data.get("sentiment_percentages", {})
        positive = float(sentiment.get("positive", 0))
        negative = float(sentiment.get("negative", 0))

        # Sentiment score (0-40 points)
        sentiment_score = (positive / 100) * 40 - (negative / 100) * 20

        # Rating score (0-30 points)
        avg_rating = float(data.get("average_rating") or data.get("rating", 3.0))
        rating_score = ((avg_rating - 1) / 4) * 30  # scale 1-5 to 0-30

        # Feature breadth score (0-20 points)
        features = data.get("features") or []
        feature_score = min(len(features) * 2, 20)

        # Trend bonus (0-10 points)
        trend = data.get("sentiment_trend", "stable")
        trend_score = 10 if trend == "improving" else (5 if trend == "stable" else 0)

        raw = sentiment_score + rating_score + feature_score + trend_score

        return {
            "app_name": app_name,
            "raw_score": max(raw, 0),
            "score": 0,  # filled after normalization
            "breakdown": {
                "sentiment": round(sentiment_score, 1),
                "rating": round(rating_score, 1),
                "features": round(feature_score, 1),
                "trend": round(trend_score, 1),
            },
            "sentiment_trend": trend,
            "average_rating": avg_rating,
        }

    def _generate_recommendations(
        self, rankings: List[Dict[str, Any]], analysis_data: Dict[str, Any]
    ) -> List[str]:
        provider = os.getenv("LLM_PROVIDER", "gemini")
        try:
            client = create_llm_client(provider)
            prompt = f"""Given this competitive app analysis, provide 4-5 specific, actionable recommendations for the lowest-ranked apps to improve.

Rankings (best to worst):
{json.dumps(rankings, indent=2)}

Detailed analysis:
{json.dumps({k: {
    'pain_points': v.get('pain_points', []),
    'features_liked': v.get('features_liked', []),
    'top_requested': v.get('top_requested', []),
} for k, v in analysis_data.items()}, indent=2)}

Return plain text bullet points."""

            return client.complete(
                "You are a mobile product strategist.", prompt
            ).strip().split("\n")
        except Exception:
            return ["See rankings data for competitive gaps."]
