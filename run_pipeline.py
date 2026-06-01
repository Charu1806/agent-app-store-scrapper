#!/usr/bin/env python3
"""Standalone pipeline runner — scrape + analyse all apps. Run as a cron job."""

import sys
from dotenv import load_dotenv
load_dotenv()

from skill_loader import load_skills
from agent_appstore import run_pipeline

skills = load_skills()
if not skills:
    print("❌ No skills loaded")
    sys.exit(1)

result = run_pipeline(skills)
sys.exit(0 if result.get("success") else 1)
