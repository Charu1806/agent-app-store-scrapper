"""Time-series JSON database for app analysis data."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_FILE = Path(os.getenv("DATA_FILE", "data/app_data.json"))


def _load_raw() -> Dict[str, Any]:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: Dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, default=str))


def save_analysis(
    app_name: str,
    sentiment: Dict[str, Any],
    features: List[Dict[str, Any]],
    average_rating: Optional[float],
    review_count: int,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Append a day's analysis for an app. Returns the date key used."""
    db = _load_raw()
    date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    if app_name not in db:
        db[app_name] = {}

    db[app_name][date_key] = {
        "sentiment": sentiment,
        "features": {f["name"]: f for f in features} if features else {},
        "average_rating": average_rating,
        "review_count": review_count,
        **(extra or {}),
    }
    _save_raw(db)
    return date_key


def load_historical_data(
    app_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return full historical data, optionally filtered by app names."""
    db = _load_raw()
    if app_names:
        return {k: v for k, v in db.items() if k in app_names}
    return db


def get_latest_analysis(app_name: str) -> Optional[Dict[str, Any]]:
    """Return the most recent day's data for an app."""
    db = _load_raw()
    app_data = db.get(app_name, {})
    if not app_data:
        return None
    latest_key = max(app_data.keys())
    return {"date": latest_key, **app_data[latest_key]}


def get_trend_data(app_name: str, days: int = 30) -> List[Dict[str, Any]]:
    """Return sorted list of day records within the last N days."""
    from datetime import timedelta

    db = _load_raw()
    app_data = db.get(app_name, {})
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = []
    for date_str, day in app_data.items():
        try:
            dt = datetime.strptime(date_str[:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                result.append({"date": date_str, **day})
        except ValueError:
            continue

    result.sort(key=lambda x: x["date"])
    return result


def all_app_names() -> List[str]:
    return list(_load_raw().keys())


def needs_refresh(app_name: str, max_age_hours: int = 24) -> bool:
    """True if app has no data, last scrape was stale, or last scrape had 0 reviews."""
    from datetime import timedelta

    db = _load_raw()
    app_data = db.get(app_name, {})
    if not app_data:
        return True
    latest_key = max(app_data.keys())
    latest_day = app_data[latest_key]

    # Force refresh if the saved entry has no reviews (empty scrape)
    if not latest_day.get("review_count"):
        return True

    try:
        dt = datetime.strptime(latest_key[:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - dt > timedelta(hours=max_age_hours)
    except ValueError:
        return True
