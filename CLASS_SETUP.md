# Class Setup & Pre-Requirements
### App Store Competitive Intelligence Agent — Workshop

---

## 👋 Welcome

In this workshop you will build a real AI agent from scratch that:
- Scrapes live App Store reviews (no paid API needed)
- Uses an LLM to analyze what users love and hate
- Displays competitive insights on a live dashboard
- Deploys to the internet for free

By the end you will have a running web app and understand how to build AI agents with modular skills.

**Estimated time:** 2–3 hours  
**Difficulty:** Beginner–Intermediate (some Python helpful but not required)

---

## 📋 Agenda

| # | Topic | Time |
|---|---|---|
| 1 | What are AI Agents? + Architecture overview | 15 min |
| 2 | Setup: GitHub, Python, virtual env, dependencies | 20 min |
| 3 | Build the scraper — fetch App Store reviews for free | 20 min |
| 4 | Build the LLM client — plug in Groq (free & fast) | 15 min |
| 5 | Build sentiment analysis + feature extraction skills | 25 min |
| 6 | Wire the orchestrator — round-robin scraping pipeline | 20 min |
| 7 | Build the Flask dashboard + Chart.js charts | 25 min |
| 8 | Run it locally — see live data | 10 min |
| 9 | Push to GitHub + deploy to Render | 20 min |
| 10 | Q&A + extensions (add your own apps, add new skills) | 10 min |

---

## ✅ Please Complete Before Class

Do these steps **before the workshop starts**. Each takes 2–5 minutes. If you get stuck, bring the error to class.

---

### 1. Install Python 3.10 or higher

Check if you already have it:
```bash
python3 --version
```

If you see `Python 3.10.x` or higher — you're good.

If not, download from [python.org/downloads](https://www.python.org/downloads/) and install.

> **Windows users:** During install, check the box **"Add Python to PATH"** — this is easy to miss.

---

### 2. Install VS Code (recommended editor)

Download from [code.visualstudio.com](https://code.visualstudio.com)

Install the **Python extension** inside VS Code:
- Open VS Code → click the Extensions icon (left sidebar)
- Search "Python" → install the one by Microsoft

---

### 3. Create a free GitHub account

1. Go to [github.com](https://github.com) → Sign up
2. Verify your email address
3. Remember your username — you'll need it in class

---

### 4. Create a free Groq account and get an API key

Groq gives you a fast, free LLM (no credit card required).

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up with Google or email
3. Click **API Keys** → **Create API Key**
4. Name it anything (e.g. "workshop")
5. Copy the key — it starts with `gsk_...`
6. Save it somewhere safe (Notes app, text file) — you'll need it in class

> ⚠️ Don't share this key publicly or commit it to GitHub.

---

### 5. Verify pip works

```bash
pip3 --version
```

You should see something like `pip 23.x.x`. If not, try `pip --version`.

---

### 6. Test your terminal

Make sure you can open a terminal and run commands:

- **Mac:** Open `Terminal` (search in Spotlight)
- **Windows:** Open `Command Prompt` or `PowerShell`
- **VS Code:** View → Terminal (works on all platforms)

Run this to confirm Python works end-to-end:
```bash
python3 -c "print('Ready!')"
```

You should see `Ready!` printed.

---

## 🛠️ What We'll Install Together in Class

You don't need to install these beforehand — we'll do it together:

```
flask          — web server for the dashboard
groq           — Groq LLM client
requests       — HTTP calls to scrape App Store
python-dotenv  — manage API keys via .env file
gunicorn       — production web server for deployment
```

---

## 💡 Good to Know (not required)

These concepts will come up. You don't need to be an expert, just familiar:

| Concept | What it means here |
|---|---|
| **API** | A URL you call to get data back (like iTunes reviews) |
| **LLM** | A language model (like ChatGPT) that reads text and responds |
| **Virtual environment** | An isolated Python sandbox so packages don't conflict |
| **JSON** | A data format — like a Python dictionary, saved as text |
| **Flask** | A lightweight Python web server |
| **Git** | Version control — tracks changes to your code |
| **Environment variable** | A secret config value stored outside your code |

---

## 🚀 What You'll Have at the End

- A working AI agent running on your laptop
- A live public URL (deployed on Render for free)
- A GitHub repo with your code
- Understanding of the agent + skills architecture pattern
- Prompts to rebuild or extend this yourself

---

## ❓ Questions Before Class?

Reach out if you're stuck on any setup step — better to sort it out before the workshop so we can spend the time building!

---

## 📎 Links to Bookmark

| Resource | URL |
|---|---|
| Workshop code | https://github.com/Charu1806/agent-app-store-scrapper |
| Full teaching guide | https://github.com/Charu1806/agent-app-store-scrapper/blob/main/TEACHING_GUIDE.md |
| Groq (free LLM) | https://console.groq.com |
| Python download | https://python.org/downloads |
| VS Code download | https://code.visualstudio.com |
| Render (free hosting) | https://render.com |
| GitHub | https://github.com |
