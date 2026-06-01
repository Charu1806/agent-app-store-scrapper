# App Store Competitive Intelligence Agent

A Python agent that scrapes Apple App Store reviews, runs LLM-powered sentiment and feature analysis, and serves a live interactive dashboard — all for free, no paid APIs needed.

## What It Does

- Scrapes reviews for multiple apps using Apple's internal iTunes API (free, no key needed)
- Runs sentiment analysis (positive / negative / neutral) using Groq LLM
- Extracts product features users love and hate
- Tracks trends over time — every pipeline run adds a new data point
- Scores and ranks competitors 0–100
- Serves a 5-tab Chart.js dashboard: Sentiment, Features, Trends, Competitive, Raw Data

## Apps Monitored (default)

- Wealthfront — Save & Invest
- Public — Invest & Trade
- Acorns — Save & Invest Money

Change `APPS_TO_MONITOR` in `.env` to monitor any App Store apps.

## Architecture

```
agent_appstore.py               ← orchestrator: scrape → analyse → save → serve
├── skills/
│   ├── app_store_scraper.py    ← iTunes internal API, no key needed
│   ├── sentiment_analyzer.py   ← LLM: positive / negative / neutral %
│   ├── feature_extractor.py    ← LLM: what users love and hate
│   ├── trend_analyzer.py       ← sentiment direction over time
│   └── competitive_scorer.py  ← ranks apps 0–100
├── database.py                 ← JSON time-series storage (per-run timestamps)
├── dashboard.py                ← Flask API + static file server
├── llm_client.py               ← unified LLM client (Groq / Gemini / Mistral / Ollama / Claude)
├── skill_loader.py             ← auto-discovers and loads skill classes
├── static/dashboard.html       ← Chart.js 5-tab interactive dashboard
├── run_pipeline.py             ← standalone scrape + analyse script
└── start.sh                    ← startup: run pipeline first, then gunicorn
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Charu1806/agent-app-store-scrapper.git
cd agent-app-store-scrapper

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env — set LLM_PROVIDER=groq and add your GROQ_API_KEY

# 5. Run
python agent_appstore.py
# Dashboard opens at http://localhost:5000
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | LLM backend: `groq` / `gemini` / `mistral` / `ollama` / `claude` |
| `GROQ_API_KEY` | — | Required if using Groq (recommended) |
| `GEMINI_API_KEY` | — | Required if using Gemini |
| `APPS_TO_MONITOR` | 3 finance apps | Comma-separated App Store URLs |
| `MAX_REVIEWS_PER_APP` | `100` | Reviews scraped per app per run |
| `MAX_AGE_HOURS` | `24` | Hours before re-scraping an app |
| `DATA_FILE` | `data/app_data.json` | Path to JSON database |
| `DASHBOARD_PORT` | `5000` | Local dashboard port |

## Supported LLM Providers

| Provider | Env Key | Free Tier |
|---|---|---|
| **Groq** | `GROQ_API_KEY` | ✅ Fast, recommended |
| Gemini | `GEMINI_API_KEY` | ✅ Yes |
| Mistral | `MISTRAL_API_KEY` | ✅ Yes |
| Ollama | runs locally | ✅ Fully local |
| Claude | `ANTHROPIC_API_KEY` | ❌ Paid |

## Deploying to Render (free)

1. Push to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service** → connect your repo
3. Set **Start Command** to `bash start.sh`
4. Add environment variables: `LLM_PROVIDER`, `GROQ_API_KEY`, `APPS_TO_MONITOR`
5. Deploy — pipeline runs on every startup, then dashboard goes live

> **Note:** Render's free tier has an ephemeral filesystem — data resets on redeploy. For persistence, add a Render Disk or use a hosted database like Supabase.

## How the Scraper Works

Uses Apple's undocumented iTunes review API — free, no authentication needed:

```
GET https://itunes.apple.com/WebObjects/MZStore.woa/wa/userReviewsRow
    ?id={app_id}&displayable-kind=11&startIndex={start}&endIndex={end}&sort=4

Headers:
    X-Apple-Store-Front: 143441-1,32
    User-Agent: iTunes/12.0 (Macintosh; OS X 10.10)
```

Reviews are scraped in round-robin batches of 10 across all apps simultaneously, up to `MAX_REVIEWS_PER_APP` total per app.

## Adding a New App

Add any App Store URL to `APPS_TO_MONITOR` in `.env`:

```
APPS_TO_MONITOR=https://apps.apple.com/us/app/robinhood/id938020774,https://apps.apple.com/us/app/acorns-save-invest-money/id883324671
```

## Adding a New Skill

1. Create `skills/my_skill.py` extending `BaseSkill`
2. Implement `name`, `description`, `input_schema`, and `execute()`
3. `skill_loader.py` auto-discovers it — no registration needed
