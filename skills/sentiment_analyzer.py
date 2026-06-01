"""Sentiment analysis of App Store reviews using Gemini."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from llm_client import create_llm_client, parse_json_response
from skills.base_skill import BaseSkill

load_dotenv()


class SentimentAnalyzerSkill(BaseSkill):
    """Analyze positive/negative/neutral sentiment of App Store reviews."""

    @property
    def name(self) -> str:
        return "analyze_app_store_sentiment"

    @property
    def description(self) -> str:
        return (
            "Analyze sentiment of App Store reviews. Returns positive/negative/neutral "
            "percentages, average score, and per-review breakdown."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Display name of the app"},
                "reviews": {"type": "array", "description": "List of review objects"},
            },
            "required": ["app_name", "reviews"],
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        app_name: str = kwargs["app_name"].strip()
        reviews: List[Dict[str, Any]] = kwargs["reviews"]

        if not reviews:
            return {"success": False, "error": f"No reviews for {app_name}"}

        provider = os.getenv("LLM_PROVIDER", "gemini")
        print(f"🧠 Sentiment analysis: {len(reviews)} reviews for {app_name} via {provider.upper()}...")

        try:
            client = create_llm_client(provider)
            sample = reviews[:50]  # token budget
            compact = [{"text": r["text"][:400], "rating": r.get("rating")} for r in sample]

            prompt = f"""Analyze sentiment of these App Store reviews for "{app_name}".

Reviews:
{json.dumps(compact, ensure_ascii=False)}

Return ONLY valid JSON:
{{
  "positive": <0-100>,
  "negative": <0-100>,
  "neutral": <0-100>,
  "average_score": <0.0-1.0 where 1.0=most positive>,
  "summary": "<2 sentence summary of overall sentiment>",
  "notable_positives": ["<thing users love>", ...],
  "notable_negatives": ["<thing users hate>", ...]
}}
The three percentages must sum to 100."""

            raw = client.complete(
                "You are a sentiment analyst. Respond with valid JSON only.", prompt
            )
            parsed = parse_json_response(raw)

            result = {
                "app_name": app_name,
                "review_count": len(reviews),
                "sentiment_percentages": {
                    "positive": float(parsed.get("positive", 0)),
                    "negative": float(parsed.get("negative", 0)),
                    "neutral": float(parsed.get("neutral", 0)),
                },
                "average_score": float(parsed.get("average_score", 0.5)),
                "summary": parsed.get("summary", ""),
                "notable_positives": list(parsed.get("notable_positives") or []),
                "notable_negatives": list(parsed.get("notable_negatives") or []),
            }
            print(f"✅ Sentiment done for {app_name}")
            return {"success": True, "data": result}

        except Exception as exc:
            return {"success": False, "error": str(exc)}
