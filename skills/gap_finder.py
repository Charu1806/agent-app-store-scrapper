"""Identify competitive gaps and product opportunities from multi-app analysis."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from llm_client import create_llm_client, parse_json_response
from skills.base_skill import BaseSkill

load_dotenv()


class GapFinderSkill(BaseSkill):
    """Compare apps and recommend market opportunities."""

    @property
    def name(self) -> str:
        return "find_market_gaps"

    @property
    def description(self) -> str:
        return (
            "Compare competitive analysis across multiple investing apps. "
            "Identify winners/losers, unmet market needs, and product recommendations."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "competitive_data": {
                    "type": "object",
                    "description": (
                        "Map of app name to analysis results including sentiment, "
                        "pain points, features, and summaries"
                    ),
                },
                "market_context": {
                    "type": "string",
                    "description": "Optional market segment context",
                },
            },
            "required": ["competitive_data"],
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        competitive_data: Dict[str, Any] = kwargs["competitive_data"]
        market_context = (kwargs.get("market_context") or "US retail investing apps").strip()

        if not competitive_data:
            return {"success": False, "error": "competitive_data cannot be empty"}

        if len(competitive_data) < 2:
            return {
                "success": False,
                "error": "Provide analysis for at least two apps to compare",
            }

        provider = os.getenv("LLM_PROVIDER", "gemini")
        print(
            f"🔍 Finding market gaps across {len(competitive_data)} apps "
            f"via {provider.upper()}..."
        )

        try:
            client = create_llm_client(provider)
            system_prompt = (
                "You are a senior product strategist for fintech startups. "
                "Identify defensible market opportunities from competitive review data. "
                "Respond with valid JSON only."
            )
            user_prompt = self._build_gap_prompt(competitive_data, market_context)
            raw = client.complete(system_prompt, user_prompt)
            parsed = parse_json_response(raw)
            result = self._normalize_gap_analysis(parsed)

            print("✅ Market gap analysis complete")
            return {"success": True, "data": result}

        except ValueError as exc:
            print(f"❌ JSON parse error in gap finder: {exc}")
            return {"success": False, "error": f"Failed to parse LLM JSON: {exc}"}
        except Exception as exc:
            print(f"❌ Gap finder failed: {exc}")
            return {"success": False, "error": str(exc)}

    def _build_gap_prompt(
        self, competitive_data: Dict[str, Any], market_context: str
    ) -> str:
        return f"""You are analyzing competitive intelligence for: {market_context}

Competitive analysis data (JSON):
{json.dumps(competitive_data, ensure_ascii=False, indent=2)}

Return ONLY a JSON object with this structure:
{{
  "rankings": [
    {{
      "app_name": "<name>",
      "position": "winning" | "losing" | "middle",
      "rationale": "<why based on review sentiment and themes>"
    }}
  ],
  "market_gaps": [
    {{
      "gap": "<unmet user need>",
      "evidence": "<which apps fail to address it>",
      "severity": "high" | "medium" | "low"
    }}
  ],
  "opportunities": [
    {{
      "product_idea": "<specific product or feature to build>",
      "target_audience": "<who to serve>",
      "differentiation": "<why this wins vs incumbents>"
    }}
  ],
  "recommended_focus": {{
    "what_to_build": "<single clearest product bet>",
    "who_to_target": "<primary persona>",
    "go_to_market_angle": "<one sentence positioning>"
  }},
  "executive_summary": "<3-4 sentence strategic summary>"
}}
"""

    def _normalize_gap_analysis(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "rankings": list(parsed.get("rankings") or []),
            "market_gaps": list(parsed.get("market_gaps") or []),
            "opportunities": list(parsed.get("opportunities") or []),
            "recommended_focus": parsed.get("recommended_focus") or {},
            "executive_summary": parsed.get("executive_summary", ""),
        }
