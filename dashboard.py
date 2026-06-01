"""Flask dashboard server for App Store competitive intelligence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, send_from_directory

import database as db


STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR))

    @app.route("/")
    def index():
        return send_from_directory(str(STATIC_DIR), "dashboard.html")

    @app.route("/api/apps")
    def api_apps():
        return jsonify(db.all_app_names())

    @app.route("/api/latest")
    def api_latest():
        names = db.all_app_names()
        result = {}
        for name in names:
            latest = db.get_latest_analysis(name)
            if latest:
                result[name] = latest
        return jsonify(result)

    @app.route("/api/trends/<app_name>")
    def api_trends(app_name: str):
        data = db.get_trend_data(app_name, days=30)
        return jsonify(data)

    @app.route("/api/trends/<app_name>/<int:days>")
    def api_trends_days(app_name: str, days: int):
        data = db.get_trend_data(app_name, days=days)
        return jsonify(data)

    @app.route("/api/historical")
    def api_historical():
        return jsonify(db.load_historical_data())

    @app.route("/api/competitive")
    def api_competitive():
        """Returns competitive summary for all apps."""
        names = db.all_app_names()
        result = {}
        for name in names:
            latest = db.get_latest_analysis(name)
            if latest:
                result[name] = {
                    "sentiment": latest.get("sentiment", {}),
                    "average_rating": latest.get("average_rating"),
                    "review_count": latest.get("review_count"),
                    "features": list(latest.get("features", {}).values())[:10],
                    "pain_points": latest.get("pain_points", []),
                    "features_liked": latest.get("features_liked", []),
                    "top_requested": latest.get("top_requested", []),
                }
        return jsonify(result)

    @app.route("/api/export/csv")
    def api_export_csv():
        """Export all historical data as CSV."""
        import csv
        import io

        historical = db.load_historical_data()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["app", "date", "positive_%", "negative_%", "neutral_%", "avg_rating", "review_count"])

        for app_name, date_data in historical.items():
            for date_str, day in sorted(date_data.items()):
                sent = day.get("sentiment", {})
                writer.writerow([
                    app_name,
                    date_str,
                    sent.get("positive", ""),
                    sent.get("negative", ""),
                    sent.get("neutral", ""),
                    day.get("average_rating", ""),
                    day.get("review_count", ""),
                ])

        from flask import Response
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=app_store_data.csv"},
        )

    return app


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", "5000"))
    print(f"🌐 Dashboard running at http://localhost:{port}")
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=True)
