# Multi-Agent Stock Research System

An autonomous multi-agent AI system that analyzes Indian (NSE) stocks by combining fundamental analysis, technical analysis, and news sentiment — powered by Google Gemini's function-calling capability and real-time market data.

## What This Does

Give it a stock ticker (e.g. `INFY.NS`), and it automatically:
1. Fetches and analyzes fundamental financial data (PE ratio, ROE, margins, debt, growth)
2. Compares valuation against sector benchmarks
3. Fetches and analyzes technical price data (moving averages, trend, momentum)
4. Fetches and analyzes recent news headlines for sentiment
5. Synthesizes all three into one final BUY / HOLD / SELL verdict with reasoning

No manual orchestration — each agent decides for itself which data it needs and fetches it via tool calls.

## Architecture

```
User provides ticker
        │
        ▼
┌─────────────────────────────────────────┐
│         Orchestrator (Python)            │
└─────────────────────────────────────────┘
        │
        ├──► Agent 1: Fundamental Analyst
        │     tools: get_fundamental_data, get_industry_benchmark
        │
        ├──► Agent 2: Technical Analyst
        │     tools: get_technical_data
        │
        ├──► Agent 3: News/Sentiment Analyst
        │     tools: get_news_data
        │
        └──► Agent 4: Chief Analyst (synthesizer)
              tools: none — reasons over Agents 1-3's output
              │
              ▼
         Final Verdict (BUY / HOLD / SELL)
```

Each specialist agent has its own role (system instruction) and its own tools. The Chief agent has no tools — its job is purely to weigh the other three outputs and resolve conflicts.

## Tech Stack

- **Google Gemini API** (`google-genai`) — LLM + function calling
- **yfinance** — real-time and historical stock data (NSE)
- **python-dotenv** — environment variable management

## Setup

```bash
git clone <your-repo-url>
cd "Multi AI sys"
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

**Never commit `.env`.** It's already listed in `.gitignore` — verify it's not tracked with `git status` before your first commit.

## Usage

```bash
python main.py
```
Enter any NSE ticker (with `.NS` suffix) when prompted, e.g. `TCS.NS`, `RELIANCE.NS`, `HAL.NS`.

## Known Limitations

- **Industry PE benchmarks are static reference values**, not live-calculated — real industry-average PE requires a paid data provider (Screener.in, Trendlyne). The system explicitly labels this data as "estimated" vs "verified" tool data.
- **Sector classification comes from Yahoo Finance's taxonomy**, which can occasionally misclassify companies (e.g. some equipment manufacturers get grouped under "Technology" instead of their actual industry) — the benchmark comparison is only as accurate as this upstream classification.
- **News sentiment is based on recent headlines only**, not full article analysis — it's a directional signal, not a comprehensive sentiment score.
- **Free tier Gemini API** has daily and per-minute quota limits — heavy testing can exhaust the daily quota; the system retries automatically on rate limits and server errors but cannot bypass a fully exhausted daily quota.

## Future Improvements

- Live industry PE data via a proper financial data API
- Peer-company comparison (not just sector average)
- Persistent conversation memory across multiple ticker queries in one session
- Web dashboard instead of terminal interface

## Author

Built as a hands-on learning project to understand multi-agent orchestration, LLM function calling, and production-grade data pipeline hygiene (sanitization, retry logic, error diagnosis).
