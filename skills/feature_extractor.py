"""Extract features mentioned in App Store reviews using Gemini."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from llm_client import create_llm_client, parse_json_response
from skills.base_skill import BaseSkill

load_dotenv()


class FeatureExtractorSkill(BaseSkill):
    """Identify product features mentioned in reviews and their sentiment."""

    @property
    def name(self) -> str:
        return "extract_app_features"

    @property
    def description(self) -> str:
        return (
            "Extract product features mentioned in App Store reviews. "
            "Returns feature frequency, sentiment per feature, and feature gaps."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {"type": "string"},
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
        print(f"🔍 Feature extraction: {len(reviews)} reviews for {app_name}...")

        try:
            client = create_llm_client(provider)
            sample = reviews[:60]
            texts = [r["text"][:300] for r in sample]

            prompt = f"""Extract product features mentioned in these App Store reviews for "{app_name}".

Reviews (one per line):
{json.dumps(texts, ensure_ascii=False)}

Return ONLY valid JSON with this structure:
{{
  "features": [
    {{
      "name": "<feature name, e.g. 'performance', 'UI design', 'notifications'>",
      "count": <number of reviews mentioning this feature>,
      "positive_mentions": <count mentioned positively>,
      "negative_mentions": <count mentioned negatively>,
      "example_quotes": ["<short quote>", "<short quote>"]
    }}
  ],
  "top_requested": ["<feature users want but don't have>", ...],
  "summary": "<2 sentence summary of feature landscape>"
}}

Include 8-15 distinct features. Only include features with at least 2 mentions."""

            raw = client.complete(
                "You are a product analyst. Respond with valid JSON only.", prompt
            )
            parsed = parse_json_response(raw)

            features = parsed.get("features") or []
            # Sort by count descending
            features.sort(key=lambda f: f.get("count", 0), reverse=True)

            result = {
                "app_name": app_name,
                "review_count": len(reviews),
                "features": features,
                "top_requested": list(parsed.get("top_requested") or []),
                "summary": parsed.get("summary", ""),
            }
            print(f"✅ Feature extraction done for {app_name}: {len(features)} features found")
            return {"success": True, "data": result}

        except Exception as exc:
            return {"success": False, "error": str(exc)}
