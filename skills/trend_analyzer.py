"""Analyze trends over time from historical app data."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from llm_client import create_llm_client, parse_json_response
from skills.base_skill import BaseSkill

load_dotenv()


class TrendAnalyzerSkill(BaseSkill):
    """Identify sentiment and feature trends over time across apps."""

    @property
    def name(self) -> str:
        return "analyze_trends"

    @property
    def description(self) -> str:
        return (
            "Analyze historical trends in sentiment and features across apps. "
            "Detects improving/declining sentiment, spikes in complaints, and new topics."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "historical_data": {
                    "type": "object",
                    "description": "Dict of app_name -> {date -> {sentiment, features, ...}}",
                },
                "window_days": {
                    "type": "integer",
                    "description": "Days of history to analyze (default 30)",
                },
            },
            "required": ["historical_data"],
        }

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        historical_data: Dict[str, Any] = kwargs["historical_data"]
        window_days: int = int(kwargs.get("window_days", 30))

        if not historical_data:
            return {"success": False, "error": "No historical data provided"}

        trends: Dict[str, Any] = {}
        alerts: List[str] = []

        for app_name, date_data in historical_data.items():
            app_trend = self._compute_app_trend(app_name, date_data, window_days)
            trends[app_name] = app_trend
            alerts.extend(app_trend.get("alerts", []))

        # LLM insight layer
        insight = self._generate_insight(trends)

        return {
            "success": True,
            "data": {
                "trends": trends,
                "alerts": alerts,
                "insight": insight,
                "window_days": window_days,
            },
        }

    def _compute_app_trend(
        self, app_name: str, date_data: Dict[str, Any], window_days: int
    ) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        # Filter and sort dates within window
        dated: List[tuple] = []
        for date_str, day_data in date_data.items():
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    dated.append((dt, day_data))
            except ValueError:
                continue

        dated.sort(key=lambda x: x[0])

        if not dated:
            return {"app_name": app_name, "data_points": 0, "trend": "insufficient_data"}

        # Build time-series arrays
        dates_str: List[str] = []
        positive_series: List[float] = []
        negative_series: List[float] = []
        rating_series: List[float] = []

        for dt, day in dated:
            dates_str.append(dt.strftime("%Y-%m-%d"))
            sent = day.get("sentiment", {})
            positive_series.append(float(sent.get("positive", 0)))
            negative_series.append(float(sent.get("negative", 0)))
            if day.get("average_rating") is not None:
                rating_series.append(float(day["average_rating"]))

        # Trend direction: compare last 7 days vs prior 7 days
        alerts: List[str] = []
        sentiment_trend = "stable"
        if len(positive_series) >= 2:
            first_half = positive_series[: len(positive_series) // 2]
            second_half = positive_series[len(positive_series) // 2 :]
            avg_first = sum(first_half) / len(first_half)
            avg_last = sum(second_half) / len(second_half)
            delta = avg_last - avg_first
            if delta > 5:
                sentiment_trend = "improving"
            elif delta < -5:
                sentiment_trend = "declining"
                alerts.append(
                    f"{app_name}: sentiment declined {abs(delta):.1f}% over {window_days} days"
                )

        # Spike detection: last point 15% worse than average
        if len(negative_series) >= 3:
            avg_neg = sum(negative_series[:-1]) / len(negative_series[:-1])
            if negative_series[-1] > avg_neg + 15:
                alerts.append(f"{app_name}: negative sentiment spike detected ({negative_series[-1]:.0f}%)")

        # Feature trends (top features most recently mentioned)
        feature_trend: Dict[str, Any] = {}
        if dated:
            _, latest_day = dated[-1]
            feature_trend = latest_day.get("features", {})

        return {
            "app_name": app_name,
            "data_points": len(dated),
            "dates": dates_str,
            "positive_series": positive_series,
            "negative_series": negative_series,
            "rating_series": rating_series,
            "sentiment_trend": sentiment_trend,
            "latest_features": feature_trend,
            "alerts": alerts,
        }

    def _generate_insight(self, trends: Dict[str, Any]) -> str:
        provider = os.getenv("LLM_PROVIDER", "gemini")
        try:
            client = create_llm_client(provider)
            compact = {
                k: {
                    "trend": v.get("sentiment_trend"),
                    "data_points": v.get("data_points"),
                    "alerts": v.get("alerts"),
                }
                for k, v in trends.items()
            }
            raw = client.complete(
                "You are a mobile app market analyst.",
                f"Given these app sentiment trends, write 3-4 bullet points of key insights:\n{json.dumps(compact, indent=2)}",
            )
            return raw.strip()
        except Exception:
            return "Trend analysis complete. See chart data for details."
