#!/usr/bin/env python3
"""App Store Competitive Intelligence Agent — orchestrates scraping, analysis, and dashboard."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from dotenv import load_dotenv

import database as db
from skill_loader import load_skills, get_skill_by_name

load_dotenv()

APPS_TO_MONITOR = [
    a.strip()
    for a in os.getenv(
        "APPS_TO_MONITOR",
        "https://apps.apple.com/us/app/wealthfront-save-and-invest/id816020992,"
        "https://apps.apple.com/us/app/public-invest-trade/id1204112719,"
        "https://apps.apple.com/us/app/acorns-save-invest-money/id883324671",
    ).split(",")
    if a.strip()
]
MAX_REVIEWS = int(os.getenv("MAX_REVIEWS_PER_APP", "50"))
MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "24"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))


def _run(skills, name: str, **kwargs) -> Dict[str, Any]:
    skill = get_skill_by_name(skills, name)
    if not skill:
        return {"success": False, "error": f"Skill not found: {name}"}
    return skill.run(**kwargs)


def _app_display_name(app_input: str) -> str:
    """
    Derive a human-readable name from a numeric ID or App Store URL.
      816020992                                    -> "816020992"
      https://apps.apple.com/.../wealthfront-.../id816020992 -> "Wealthfront"
    """
    import re
    app_input = app_input.strip().rstrip("#productRatings").strip()
    # Extract slug from URL: .../wealthfront-save-and-invest/id...
    m = re.search(r"/app/([^/]+)/id\d+", app_input)
    if m:
        slug = m.group(1)          # e.g. "wealthfront-save-and-invest"
        return slug.split("-")[0].capitalize()
    # Plain numeric or bundle ID
    return app_input.split(".")[-1].capitalize() if "." in app_input else app_input


def _scrape_all_apps_round_robin(skills, apps: List[Dict], max_per_app: int, batch_size: int = 10) -> Dict[str, List]:
    """
    Fetch reviews in round-robin batches across all apps.
    Page 1 for all apps → Page 2 for all apps → ... until max_per_app reached.
    """
    from skills.app_store_scraper import parse_app_store_input
    import time

    reviews_by_app: Dict[str, List] = {a["name"]: [] for a in apps}
    seen_ids: Dict[str, set] = {a["name"]: set() for a in apps}
    pages_needed = (max_per_app + batch_size - 1) // batch_size  # ceil division

    for page in range(1, pages_needed + 1):
        print(f"\n{'─'*50}")
        print(f"📦 Round {page}/{pages_needed} — fetching page {page} for all apps")
        print(f"{'─'*50}")

        all_done = True
        for app in apps:
            app_name = app["name"]
            app_id = app["id"]

            if len(reviews_by_app[app_name]) >= max_per_app:
                print(f"   ⏩ {app_name}: already has {len(reviews_by_app[app_name])} reviews, skipping")
                continue

            all_done = False
            print(f"   📱 {app_name} — page {page}...")
            scraped = _run(skills, "scrape_app_store_reviews", app_id=app_id, max_reviews=batch_size, page=page)

            if not scraped.get("success"):
                print(f"   ❌ {app_name}: {scraped.get('error')}")
                continue

            batch = scraped["data"]["reviews"]
            new = [r for r in batch if r.get("id") not in seen_ids[app_name]]
            for r in new:
                seen_ids[app_name].add(r.get("id"))
            reviews_by_app[app_name].extend(new)
            print(f"   ✅ {app_name}: +{len(new)} new (total {len(reviews_by_app[app_name])})")

            if len(batch) < batch_size:
                print(f"   ✅ {app_name}: reached end of reviews")

        if all_done:
            break

    return reviews_by_app


def run_pipeline(skills) -> Dict[str, Any]:
    """Full scrape → sentiment → features → trend → score pipeline."""
    analysis_data: Dict[str, Any] = {}

    # Build app list, skip fresh ones
    apps_to_scrape = []
    for app_id in APPS_TO_MONITOR:
        app_name = _app_display_name(app_id)
        if not db.needs_refresh(app_name, MAX_AGE_HOURS):
            print(f"⏩ {app_name}: data is fresh, skipping scrape")
            latest = db.get_latest_analysis(app_name)
            if latest:
                analysis_data[app_name] = latest
        else:
            apps_to_scrape.append({"name": app_name, "id": app_id})

    # Round-robin scrape: 10 per app per round, up to MAX_REVIEWS total
    if apps_to_scrape:
        print(f"\n🔄 Round-robin scraping {len(apps_to_scrape)} apps, {MAX_REVIEWS} reviews each (10/round)")
        reviews_by_app = _scrape_all_apps_round_robin(
            skills, apps_to_scrape, max_per_app=MAX_REVIEWS, batch_size=10
        )
    else:
        reviews_by_app = {}

    # Analyse each app
    for app in apps_to_scrape:
        app_name = app["name"]
        reviews = reviews_by_app.get(app_name, [])

        print(f"\n{'='*50}")
        print(f"🔬 Analysing {app_name} ({len(reviews)} reviews)")
        print(f"{'='*50}")

        if not reviews:
            print(f"   ⚠️  No reviews — skipping analysis")
            continue

        print(f"   ✅ {len(reviews)} reviews scraped")

        # 2. Sentiment
        print(f"   🧠 Analyzing sentiment...")
        sentiment_result = _run(skills, "analyze_app_store_sentiment", app_name=app_name, reviews=reviews)
        sentiment = {}
        notable_pos, notable_neg = [], []
        if sentiment_result.get("success"):
            d = sentiment_result["data"]
            sentiment = d.get("sentiment_percentages", {})
            notable_pos = d.get("notable_positives", [])
            notable_neg = d.get("notable_negatives", [])
            pct = sentiment
            print(f"   ✅ Sentiment: +{pct.get('positive',0):.0f}% / -{pct.get('negative',0):.0f}% / ~{pct.get('neutral',0):.0f}%")
        else:
            print(f"   ⚠️  Sentiment failed: {sentiment_result.get('error')}")

        # 3. Features
        print(f"   🔍 Extracting features...")
        feature_result = _run(skills, "extract_app_features", app_name=app_name, reviews=reviews)
        features = []
        top_requested = []
        if feature_result.get("success"):
            features = feature_result["data"].get("features", [])
            top_requested = feature_result["data"].get("top_requested", [])
            print(f"   ✅ {len(features)} features extracted")
        else:
            print(f"   ⚠️  Feature extraction failed: {feature_result.get('error')}")

        # Compute average rating from reviews
        ratings = [r["rating"] for r in reviews if r.get("rating") is not None]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

        # 4. Persist
        date_key = db.save_analysis(
            app_name=app_name,
            sentiment=sentiment,
            features=features,
            average_rating=avg_rating,
            review_count=len(reviews),
            extra={
                "notable_positives": notable_pos,
                "notable_negatives": notable_neg,
                "top_requested": top_requested,
                "pain_points": notable_neg,
                "features_liked": notable_pos,
            },
        )
        print(f"   💾 Saved to database ({date_key})")

        analysis_data[app_name] = {
            "sentiment": sentiment,
            "sentiment_percentages": sentiment,
            "features": features,
            "average_rating": avg_rating,
            "review_count": len(reviews),
            "pain_points": notable_neg,
            "features_liked": notable_pos,
            "top_requested": top_requested,
        }
        any_refreshed = True

    # 5. Trend analysis
    print(f"\n📈 Running trend analysis...")
    historical = db.load_historical_data()
    trend_result = _run(skills, "analyze_trends", historical_data=historical, window_days=30)
    trends = {}
    if trend_result.get("success"):
        trend_data = trend_result["data"]
        trends = trend_data.get("trends", {})
        alerts = trend_data.get("alerts", [])
        if alerts:
            print("\n🚨 ALERTS:")
            for alert in alerts:
                print(f"   • {alert}")
        insight = trend_data.get("insight", "")
        if insight:
            print(f"\n💡 Trend Insight:\n{insight}")

    # Merge trend direction into analysis_data
    for app_name in analysis_data:
        if app_name in trends:
            analysis_data[app_name]["sentiment_trend"] = trends[app_name].get("sentiment_trend", "stable")

    # 6. Competitive scoring
    if len(analysis_data) >= 2:
        print(f"\n🏆 Computing competitive scores...")
        score_result = _run(skills, "score_competitors", analysis_data=analysis_data)
        if score_result.get("success"):
            d = score_result["data"]
            rankings = d.get("rankings", [])
            print("\n📊 RANKINGS:")
            for r in rankings:
                print(f"   {r['score']:5.1f}/100  {r['app_name']}  (trend: {r.get('sentiment_trend','?')})")
            winner = d.get("winner")
            if winner:
                print(f"\n🥇 Winner: {winner}")
            recs = d.get("recommendations", [])
            if recs:
                print("\n💼 Recommendations:")
                for rec in recs[:5]:
                    if rec.strip():
                        print(f"   {rec}")

    return {"success": True, "analysis_data": analysis_data, "trends": trends}


def main() -> int:
    print("=" * 60)
    print("📊 App Store Competitive Intelligence Agent")
    print(f"   Apps: {', '.join(_app_display_name(a) for a in APPS_TO_MONITOR)}")
    print(f"   Max reviews/app: {MAX_REVIEWS}")
    print("=" * 60)

    skills = load_skills()
    if not skills:
        print("❌ No skills loaded")
        return 1

    print(f"\n✅ Loaded {len(skills)} skills: {', '.join(s.name for s in skills)}\n")

    try:
        result = run_pipeline(skills)
        if not result.get("success"):
            print(f"\n❌ Pipeline failed: {result.get('error')}")
            return 1

        print(f"\n{'='*60}")
        print(f"✅ Analysis complete! Starting dashboard...")
        print(f"   👉  http://localhost:{DASHBOARD_PORT}")
        print(f"{'='*60}\n")

        # Start dashboard
        from dashboard import create_app
        app = create_app()
        app.run(host="0.0.0.0", port=DASHBOARD_PORT, debug=False)

    except KeyboardInterrupt:
        print("\n👋 Shutting down")
        return 0
    except Exception as exc:
        print(f"❌ {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
