# How to Build an App Store Competitive Intelligence Agent
### A step-by-step guide for builders and learners

---

## What You'll Build

A Python system that:
1. Scrapes App Store reviews for any app (free, no API key)
2. Uses an LLM to analyze sentiment and extract product insights
3. Stores results in a time-series database
4. Serves a live dashboard with charts and competitive rankings

---

## Prerequisites

- Python 3.10+
- A free [Groq account](https://console.groq.com) for LLM access
- A free [GitHub account](https://github.com) to store your code
- A text editor (VS Code recommended)

---

## Part 1 — Setup

### Step 1: Create a GitHub account
1. Go to [github.com](https://github.com) → Sign up
2. Verify your email
3. Create a new repository: click **+** → **New repository**
   - Name it: `app-store-intelligence`
   - Set to Public
   - Check "Add a README file"
   - Click **Create repository**

### Step 2: Clone the repo locally
```bash
git clone https://github.com/YOUR_USERNAME/app-store-intelligence.git
cd app-store-intelligence
```

### Step 3: Create a virtual environment
```bash
# Create
python3 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# You should see (venv) in your terminal prompt
```

### Step 4: Create requirements.txt
Create a file called `requirements.txt` in your project folder:

```
python-dotenv>=1.0.0
requests>=2.31.0
flask>=3.0.0
gunicorn>=21.0.0
groq>=0.9.0
google-genai>=1.0.0
```

Install everything:
```bash
pip install -r requirements.txt
```

### Step 5: Get a free Groq API key
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / Log in
3. Go to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

### Step 6: Create your .env file
Create a file called `.env` (never commit this to GitHub):

```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here

APPS_TO_MONITOR=https://apps.apple.com/us/app/wealthfront-save-and-invest/id816020992,https://apps.apple.com/us/app/public-invest-trade/id1204112719,https://apps.apple.com/us/app/acorns-save-invest-money/id883324671

MAX_REVIEWS_PER_APP=50
MAX_AGE_HOURS=24
DATA_FILE=data/app_data.json
DASHBOARD_PORT=5000
```

Create a `.gitignore` file so secrets aren't pushed to GitHub:
```
.env
venv/
__pycache__/
data/
*.pyc
.DS_Store
```

---

## Part 2 — Build It

You have two paths:

---

### PATH A: Build it manually (file by file)

Use these prompts with any AI assistant (Claude, ChatGPT, Cursor, etc.) to build each piece.

---

#### Prompt 1 — The LLM Client

> **Paste this prompt into your AI assistant:**
>
> Build a Python file called `llm_client.py` that provides a unified LLM client factory. It should:
> - Have a function `create_llm_client(provider=None)` that reads `LLM_PROVIDER` from the environment
> - Return an object with a `.complete(system, user) -> str` method
> - Support at minimum: groq (using the `groq` package, model `llama-3.3-70b-versatile`), gemini (using `google.genai`, model `gemini-2.5-flash-preview-05-20`), and ollama (local HTTP API)
> - Raise `ValueError` with a clear message if the API key is missing
> - Also include a `parse_json_response(text)` helper that extracts JSON from LLM responses that may include markdown code fences

---

#### Prompt 2 — The App Store Scraper

> **Paste this prompt into your AI assistant:**
>
> Build a Python file called `scraper.py` that scrapes Apple App Store reviews without any API key. Use Apple's internal iTunes review API:
>
> URL: `https://itunes.apple.com/WebObjects/MZStore.woa/wa/userReviewsRow?id={app_id}&displayable-kind=11&startIndex={start}&endIndex={end}&sort=4`
>
> Headers required:
> - `X-Apple-Store-Front: 143441-1,32`
> - `User-Agent: iTunes/12.0 (Macintosh; OS X 10.10)`
> - `Accept: application/json`
>
> The function should:
> - Accept an app ID (numeric string) or full App Store URL
> - Accept a page number and page size (default 10)
> - Return a list of reviews with fields: id, text, title, rating (1-5), author, date
> - Parse the numeric app ID from a URL like `https://apps.apple.com/us/app/wealthfront-save-and-invest/id816020992`
> - Handle errors gracefully and return an empty list on failure

---

#### Prompt 3 — Sentiment Analysis

> **Paste this prompt into your AI assistant:**
>
> Build a Python function called `analyze_sentiment(app_name, reviews, llm_client)` in a file called `sentiment.py`.
>
> It should:
> - Take a list of review dicts (each has `text` and `rating` fields)
> - Sample up to 50 reviews to stay within token limits
> - Send them to the LLM with a prompt asking for sentiment analysis
> - Return a dict with: `positive` (0-100), `negative` (0-100), `neutral` (0-100), `summary` (2 sentences), `notable_positives` (list of strings), `notable_negatives` (list of strings)
> - The three percentages must sum to 100
> - Use `parse_json_response` to extract the JSON from the LLM response

---

#### Prompt 4 — Feature Extraction

> **Paste this prompt into your AI assistant:**
>
> Build a Python function called `extract_features(app_name, reviews, llm_client)` in a file called `features.py`.
>
> It should:
> - Take a list of review dicts
> - Send them to the LLM asking it to identify the top product features mentioned
> - Return a list of feature dicts, each with: `name`, `count` (how many reviews mention it), `positive_mentions`, `negative_mentions`, `example_quotes` (up to 2)
> - Also return a `top_requested` list of features users wish the app had
> - Use `parse_json_response` to extract JSON from the LLM response

---

#### Prompt 5 — JSON Database

> **Paste this prompt into your AI assistant:**
>
> Build a Python file called `database.py` for a simple JSON time-series database. It should store data in a file at the path set by the `DATA_FILE` environment variable (default: `data/app_data.json`).
>
> Structure: `{ "AppName": { "YYYY-MM-DD HH:MM": { ...analysis data... } } }`
>
> Include these functions:
> - `save_analysis(app_name, sentiment, features, average_rating, review_count, extra=None) -> str` — saves and returns the timestamp key used
> - `get_latest_analysis(app_name) -> dict` — returns the most recent entry
> - `load_historical_data() -> dict` — returns all data
> - `all_app_names() -> list`
> - `needs_refresh(app_name, max_age_hours=24) -> bool` — returns True if no data, data is older than max_age_hours, or last entry had 0 reviews
>
> The timestamp key format must be `YYYY-MM-DD HH:MM` so each pipeline run creates a new entry (enabling trend charts).

---

#### Prompt 6 — The Orchestrator

> **Paste this prompt into your AI assistant:**
>
> Build a Python file called `main.py` that orchestrates the full pipeline:
>
> 1. Read `APPS_TO_MONITOR` (comma-separated App Store URLs) from environment
> 2. For each app, check if it needs a refresh using the database
> 3. Scrape reviews in round-robin batches of 10 across all apps (fetch 10 for App A, then 10 for App B, then 10 for App C, then repeat) up to `MAX_REVIEWS_PER_APP` total per app
> 4. For each app with reviews: run sentiment analysis, run feature extraction, save to database
> 5. After all apps: run a competitive ranking that scores each app 0-100 based on sentiment and review volume
> 6. Print clear progress output with emojis at each step
>
> Use the functions from `scraper.py`, `sentiment.py`, `features.py`, `database.py`, and `llm_client.py`.

---

#### Prompt 7 — The Flask Dashboard

> **Paste this prompt into your AI assistant:**
>
> Build a Flask web server in `dashboard.py` that serves a competitive intelligence dashboard. It should have these API endpoints:
> - `GET /` — serve `static/dashboard.html`
> - `GET /api/apps` — list all app names in the database
> - `GET /api/latest` — return the most recent analysis for all apps
> - `GET /api/historical` — return all historical data for trend charts
> - `GET /api/export/csv` — download all data as CSV
>
> Also build `static/dashboard.html` as a single-page app using Chart.js (CDN). It should have 5 tabs:
> 1. **Sentiment** — gauge cards per app showing positive/negative/neutral %, grouped bar chart with apps on x-axis and review counts on y-axis, sentiment trend line chart over time
> 2. **Features** — horizontal bar chart of most mentioned features, positive vs negative breakdown
> 3. **Trends** — line chart of sentiment over time for all apps, rating trend, review volume
> 4. **Competitive** — ranked table with scores, radar chart comparing apps
> 5. **Raw Data** — filterable table with CSV download
>
> Use a dark theme (background #0f1117). Load data from the API endpoints on page load.

---

### PATH B: Build it with an Agent + Skills architecture

This is the more advanced pattern. Instead of flat functions, each capability is a "skill" — a self-contained class the agent can discover and call by name.

Use this single prompt with Claude, GPT-4, or any capable LLM:

---

> **Master prompt — paste this to build the full agent:**
>
> Build a multi-skill Python agent for Apple App Store competitive intelligence. The system should follow this architecture:
>
> **1. BaseSkill abstract class** (`skills/base_skill.py`)
> - Abstract properties: `name` (str), `description` (str), `input_schema` (dict, JSON Schema format)
> - Abstract method: `execute(**kwargs) -> dict`
> - Concrete `run(**kwargs) -> dict` method that wraps execute in try/except and returns `{"success": True/False, "data": ..., "error": ...}`
>
> **2. Skill implementations** (each in `skills/`):
> - `AppStoreScraperSkill` (name: `scrape_app_store_reviews`) — scrapes using iTunes internal API, accepts `app_id` (URL or numeric), `page`, `max_reviews`
> - `SentimentAnalyzerSkill` (name: `analyze_app_store_sentiment`) — LLM sentiment, returns positive/negative/neutral percentages + notable positives/negatives
> - `FeatureExtractorSkill` (name: `extract_app_features`) — LLM feature extraction, returns features list + top_requested
> - `TrendAnalyzerSkill` (name: `analyze_trends`) — computes sentiment direction from historical data, returns trend per app + alerts
> - `CompetitiveScorerSkill` (name: `score_competitors`) — scores and ranks apps 0-100, returns rankings + winner + recommendations
>
> **3. Skill loader** (`skill_loader.py`) — auto-discovers all BaseSkill subclasses in the `skills/` directory using importlib, no manual registration
>
> **4. LLM client factory** (`llm_client.py`) — `create_llm_client(provider)` supporting groq (llama-3.3-70b-versatile), gemini (google.genai, gemini-2.5-flash), mistral, ollama, and claude. Each returns an object with `.complete(system, user) -> str`. Include `parse_json_response(text)` that strips markdown fences before JSON parsing.
>
> **5. JSON time-series database** (`database.py`) — stores data keyed as `{AppName: {"YYYY-MM-DD HH:MM": {...}}}`. Functions: `save_analysis`, `get_latest_analysis`, `load_historical_data`, `all_app_names`, `needs_refresh`. Timestamp key includes HH:MM so each run is a separate data point for trend charts.
>
> **6. Orchestrator** (`agent_appstore.py`) — reads `APPS_TO_MONITOR` env var (comma-separated App Store URLs), checks which apps need refresh, scrapes in round-robin batches of 10 per app per round up to `MAX_REVIEWS_PER_APP`, then for each app runs sentiment → features → save. Finally runs trend analysis and competitive scoring across all apps.
>
> **7. Flask dashboard** (`dashboard.py`) with endpoints: `/`, `/api/apps`, `/api/latest`, `/api/historical`, `/api/export/csv`. The dashboard at `static/dashboard.html` uses Chart.js with 5 tabs: Sentiment (grouped bar by review count, trend line), Features, Trends, Competitive (radar + rankings table), Raw Data. Dark theme (#0f1117).
>
> **8. Startup script** (`start.sh`) that runs `python run_pipeline.py` first, then starts gunicorn. And `run_pipeline.py` as a standalone script that just imports and runs the pipeline.
>
> **Environment variables** (via `.env`): `LLM_PROVIDER`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `APPS_TO_MONITOR`, `MAX_REVIEWS_PER_APP` (default 100), `MAX_AGE_HOURS` (default 24), `DATA_FILE` (default `data/app_data.json`), `DASHBOARD_PORT` (default 5000).
>
> The iTunes scraper URL is:
> `https://itunes.apple.com/WebObjects/MZStore.woa/wa/userReviewsRow?id={app_id}&displayable-kind=11&startIndex={start}&endIndex={end}&sort=4`
> with headers `X-Apple-Store-Front: 143441-1,32` and `User-Agent: iTunes/12.0 (Macintosh; OS X 10.10)`.

---

## Part 3 — Push to GitHub

```bash
# Stage all files (never stage .env)
git add README.md requirements.txt .gitignore
git add *.py skills/ static/ start.sh Procfile run_pipeline.py

# Commit
git commit -m "Initial commit: App Store competitive intelligence agent"

# Push
git push origin main
```

If prompted for a password, use a **Personal Access Token** (not your GitHub password):
- GitHub → Settings → Developer settings → Personal access tokens → Generate new token
- Check the `repo` scope → Generate → copy the token
- Use it as the password when git prompts you

---

## Part 4 — Deploy to Render (free)

1. Go to [render.com](https://render.com) → **New → Web Service**
2. Connect your GitHub repo
3. Set **Start Command** to: `bash start.sh`
4. Under **Environment**, add:
   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_...
   APPS_TO_MONITOR=https://apps.apple.com/us/app/wealthfront-save-and-invest/id816020992,...
   MAX_REVIEWS_PER_APP=100
   MAX_AGE_HOURS=6
   DATA_FILE=data/app_data.json
   ```
5. Click **Create Web Service**

Your dashboard will be live at `https://your-app-name.onrender.com`.

> The pipeline runs every time Render wakes up the service (on each visit after inactivity). This keeps the data fresh without any paid cron service.

---

## Common Issues & Fixes

| Problem | Fix |
|---|---|
| 0 reviews scraped | Check the app ID is correct. Use the numeric ID from the App Store URL (`/id816020992` → `816020992`). US apps only — make sure the URL uses `/us/app/`. |
| LLM API error | Check your API key is set correctly in `.env`. For Groq, it starts with `gsk_`. |
| Dashboard shows empty data | Make sure the pipeline ran successfully. Check the terminal output for `✅ Saved to database`. |
| Gemini DNS error | Google APIs may be blocked on some networks. Switch to `LLM_PROVIDER=groq`. |
| Render dashboard is empty | Check that your env variables are set in Render → Environment. Check that **Start Command** is `bash start.sh` (not the default gunicorn command). |
| Trend chart shows dots only | This is correct for a single run. After 2+ runs the dots connect into trend lines. |

---

## Key Concepts Explained

**Why round-robin scraping?**
Apple rate-limits by IP. Fetching 10 reviews from App A, then App B, then App C before going back to App A gives time between requests and mimics normal browsing behavior.

**Why per-run timestamps in the database?**
If the key were just `YYYY-MM-DD`, running the agent twice in a day would overwrite the first run. Using `YYYY-MM-DD HH:MM` means every run adds a new data point, which is what makes the trend charts useful.

**Why a skills architecture?**
Each skill is independently testable, replaceable, and discoverable. You can swap the scraper for a different data source, or add a new analysis skill, without touching the orchestrator. The agent just calls skills by name.

**Why Groq instead of OpenAI?**
Groq is free, extremely fast (runs Llama 3.3 70B), and doesn't require a credit card. For this use case (analyzing ~50 reviews per app) it outperforms many paid options.

---

## Reference

- Live app: https://agent-app-store-scrapper.onrender.com
- Source code: https://github.com/Charu1806/agent-app-store-scrapper
- Groq console: https://console.groq.com
- Render dashboard: https://dashboard.render.com
