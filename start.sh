#!/bin/bash
set -e

echo "🔄 Running pipeline before starting server..."
python run_pipeline.py

echo "🚀 Starting dashboard..."
exec gunicorn dashboard:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
