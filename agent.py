#!/usr/bin/env python3
"""Competitive intelligence agent — orchestrates skills without implementation details."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

from skill_loader import get_skill_by_name, load_skills, skills_to_tools

load_dotenv()

TARGET_APPS = [
    {"name": "Wealthfront", "app_id": "com.wealthfront"},
    {"name": "Acorns", "app_id": "com.acorns.android"},
    {"name": "Public", "app_id": "com.public.android"},
]
MAX_REVIEWS = int(os.getenv("MAX_REVIEWS_PER_APP", "50"))


def _run(skills: List[Any], name: str, **kwargs: Any) -> Dict[str, Any]:
    skill = get_skill_by_name(skills, name)
    return skill.run(**kwargs) if skill else {"success": False, "error": f"Unknown skill: {name}"}


def run_sequential(skills: List[Any]) -> Dict[str, Any]:
    """Scrape → analyze → gap analysis (non-Claude providers)."""
    competitive: Dict[str, Any] = {}
    for app in TARGET_APPS:
        scraped = _run(skills, "scrape_reviews", app_id=app["app_id"], max_reviews=MAX_REVIEWS)
        if not scraped.get("success"):
            print(f"⚠️  {app['name']}: {scraped.get('error')}")
            continue
        analyzed = _run(
            skills, "analyze_sentiment",
            app_name=app["name"], reviews=scraped["data"]["reviews"],
        )
        if analyzed.get("success"):
            competitive[app["name"]] = analyzed["data"]
    if len(competitive) < 2:
        return {"success": False, "error": "Need at least two apps analyzed"}
    gaps = _run(
        skills, "find_market_gaps",
        competitive_data=competitive,
        market_context="US micro-investing and robo-advisor apps",
    )
    return {"success": gaps.get("success", False), "competitive_analysis": competitive, "market_insights": gaps.get("data"), "error": gaps.get("error")}


def run_claude_loop(skills: List[Any]) -> Dict[str, Any]:
    """Claude tool-use loop: model picks skills; agent executes them."""
    import anthropic

    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return {"success": False, "error": "ANTHROPIC_API_KEY required for claude orchestration"}
    client = anthropic.Anthropic(api_key=key)
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    apps = "\n".join(f"- {a['name']} ({a['app_id']})" for a in TARGET_APPS)
    messages: List[Dict[str, Any]] = [{
        "role": "user",
        "content": f"Analyze these Play Store apps:\n{apps}\nScrape up to {MAX_REVIEWS} reviews each, analyze sentiment, find market gaps. Summarize at the end.",
    }]
    print("🤖 Claude orchestration started\n")
    for turn in range(1, 16):
        print(f"   🔄 Turn {turn}")
        resp = client.messages.create(
            model=model, max_tokens=8192,
            system="Use tools to scrape, analyze, and compare investing apps. Then report findings.",
            tools=skills_to_tools(skills), messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})
        uses = [b for b in resp.content if b.type == "tool_use"]
        if not uses:
            report = "\n".join(b.text for b in resp.content if hasattr(b, "text"))
            print("\n📋 FINAL REPORT\n" + report)
            return {"success": True, "report": report}
        results = []
        for u in uses:
            print(f"   🛠️  {u.name}")
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": json.dumps(_run(skills, u.name, **u.input), default=str)})
        messages.append({"role": "user", "content": results})
    return {"success": False, "error": "Max turns exceeded"}


def main() -> int:
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    print("=" * 60, f"\n📊 Competitive Intelligence Agent | LLM: {provider.upper()}\n", "=" * 60, sep="")
    skills = load_skills()
    if not skills:
        print("❌ No skills loaded")
        return 1
    try:
        if provider == "claude":
            out = run_claude_loop(skills)
        else:
            print("⚙️  Sequential workflow\n")
            out = run_sequential(skills)
            if out.get("market_insights"):
                print("\n📋 MARKET INSIGHTS\n", json.dumps(out["market_insights"], indent=2))
            for name, data in (out.get("competitive_analysis") or {}).items():
                s = data.get("sentiment_percentages", {})
                print(f"\n{name}: 👍{s.get('positive')}% 👎{s.get('negative')}% 😐{s.get('neutral')}%")
        if out.get("error") and not out.get("success"):
            print(f"\n❌ {out['error']}")
        return 0 if out.get("success") else 1
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"❌ {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
