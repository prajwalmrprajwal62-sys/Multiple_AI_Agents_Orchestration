import os
import time
import math
import yfinance as yf
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
if not API_KEY:
    raise SystemExit("GEMINI_API_KEY is missing. Add it to your .env file before running the script.")

client = genai.Client(api_key=API_KEY)

INDUSTRY_PE_BENCHMARKS = {
    "Technology": {"typical_pe_range": "22-30", "note": "IT services sector, India (approximate reference)"},
    "Financial Services": {"typical_pe_range": "15-22", "note": "Banking/NBFC sector, India (approximate reference)"},
    "Consumer Cyclical": {"typical_pe_range": "25-40", "note": "Auto, retail sector, India (approximate reference)"},
    "Healthcare": {"typical_pe_range": "25-35", "note": "Pharma sector, India (approximate reference)"},
    "Consumer Defensive": {"typical_pe_range": "40-60", "note": "FMCG sector, India (approximate reference)"},
    "Energy": {"typical_pe_range": "10-18", "note": "Oil & gas, energy sector, India (approximate reference)"},
    "Basic Materials": {"typical_pe_range": "12-20", "note": "Metals, cement, chemicals, India (approximate reference)"},
    "Industrials": {"typical_pe_range": "20-30", "note": "Capital goods, EMS sector, India (approximate reference)"},
    "Communication Services": {"typical_pe_range": "18-28", "note": "Telecom, media, India (approximate reference)"},
}

# ─── Sanitizer ────────────────────────────────────────────────
def sanitize(data: dict) -> dict:
    clean = {}
    for key, value in data.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            clean[key] = "N/A"
        elif value is None:
            clean[key] = "N/A"
        else:
            clean[key] = value
    return clean

# ─── Tools ────────────────────────────────────────────────────
def get_fundamental_data(ticker: str) -> dict:
    """Fetches fundamental financial data for an Indian stock (PE ratio, ROE, profit margins, debt, revenue growth, sector). Ticker must use .NS suffix."""
    stock = yf.Ticker(ticker)
    try:
        info = stock.info
    except Exception as exc:
        raise RuntimeError(f"yfinance could not fetch fundamental data for {ticker}.") from exc

    return sanitize({
        "Company": info.get("longName", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "Industry": info.get("industry", "N/A"),
        "PE Ratio": info.get("trailingPE", "N/A"),
        "ROE": info.get("returnOnEquity", "N/A"),
        "Profit Margins": info.get("profitMargins", "N/A"),
        "Revenue Growth": info.get("revenueGrowth", "N/A"),
        "Debt to Equity": info.get("debtToEquity", "N/A"),
    })

def get_technical_data(ticker: str) -> dict:
    """Fetches technical price data for an Indian stock (current price, moving averages, 52-week range). Ticker must use .NS suffix."""
    stock = yf.Ticker(ticker)
    try:
        info = stock.info
        history = stock.history(period="3mo")
    except Exception as exc:
        raise RuntimeError(f"yfinance could not fetch technical data for {ticker}.") from exc

    if history.empty:
        raise RuntimeError(f"No price history for {ticker}.")

    valid_closes = history["Close"].dropna()
    current_price = round(valid_closes.iloc[-1], 2) if not valid_closes.empty else (info.get("currentPrice") or info.get("regularMarketPrice") or "N/A")

    return sanitize({
        "Current Price": current_price,
        "50 Day MA": info.get("fiftyDayAverage", "N/A"),
        "200 Day MA": info.get("twoHundredDayAverage", "N/A"),
        "52W High": info.get("fiftyTwoWeekHigh", "N/A"),
        "52W Low": info.get("fiftyTwoWeekLow", "N/A"),
    })

def get_industry_benchmark(sector: str) -> dict:
    """Returns typical PE ratio range for a sector in Indian markets. Call AFTER get_fundamental_data using its exact 'Sector' value. Static reference table, not live data."""
    data = INDUSTRY_PE_BENCHMARKS.get(sector)
    if not data:
        return {"error": f"No benchmark for sector '{sector}'. Say comparison isn't possible."}
    return data

# ─── Error Diagnosis ────────────────────────────────────────
def diagnose_error(e):
    err_str = str(e)
    print(f"[RAW ERROR — for debugging]: {err_str[:400]}\n")
    code = getattr(e, "code", None)
    status = getattr(e, "status", None)

    if code == 429 or status == "RESOURCE_EXHAUSTED" or "429" in err_str or "quota" in err_str.lower():
        return ("RATE_LIMIT", "This is YOUR usage quota, not a Google outage. Check ai.google.dev for your limits.")
    if code == 503 or status == "UNAVAILABLE" or "503" in err_str or "unavailable" in err_str.lower():
        return ("SERVER_BUSY", "Google's servers are overloaded on THEIR end. Usually clears within a minute.")
    if code == 400 or status == "INVALID_ARGUMENT" or "400" in err_str:
        return ("BAD_REQUEST", f"Malformed request — likely bad data sent to the model. Detail: {err_str[:200]}")
    return ("UNKNOWN", f"Unclassified error. Detail: {err_str[:300]}")

# ─── Generic Agent Caller (with retry + diagnosis) ───────────
def call_agent(system_instruction, user_message, tools, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                ),
            )
            return response.text
        except Exception as e:
            category, explanation = diagnose_error(e)
            print(f"[{category}] {explanation}")
            if category in ("RATE_LIMIT", "SERVER_BUSY") and attempt < max_retries:
                wait_time = 15 * (attempt + 1)
                print(f"Retrying in {wait_time}s ({attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            return f"[{category}] Could not complete this step. {explanation}"

# ─── The 3 Agents ─────────────────────────────────────────────
def run_fundamental_agent(ticker):
    system = (
        "You are a fundamental analyst for Indian stocks. Call get_fundamental_data for the ticker, "
        "then call get_industry_benchmark with the sector it returns. Give a buy/hold/sell opinion. "
        "Clearly separate VERIFIED tool data from ESTIMATED benchmark data. Be concise."
    )
    return call_agent(system, f"Analyze {ticker} fundamentally.", [get_fundamental_data, get_industry_benchmark])

def run_technical_agent(ticker):
    system = (
        "You are a technical analyst for Indian stocks. Call get_technical_data for the ticker. "
        "Analyze trend, momentum, and give short-term outlook. Be concise."
    )
    return call_agent(system, f"Analyze {ticker} technically.", [get_technical_data])

def run_chief_agent(ticker, fund_result, tech_result):
    system = (
        "You are a chief investment analyst. You're given a fundamental and a technical analysis "
        "of the same stock. Weigh both, resolve conflicts, give ONE final verdict: BUY, HOLD, or SELL "
        "with 3-4 line justification. Be decisive."
    )
    combined = f"Fundamental Analysis:\n{fund_result}\n\nTechnical Analysis:\n{tech_result}\n\nFinal verdict on {ticker}?"
    return call_agent(system, combined, [])  # no tools — pure reasoning over given text

# ─── Orchestrator — Fully Autonomous ───────────────────────────
def run_full_pipeline(ticker):
    print(f"\n[AGENT 1 — Fundamental Analyst]")
    fund_result = run_fundamental_agent(ticker)
    print(fund_result)

    print(f"\n[AGENT 2 — Technical Analyst]")
    tech_result = run_technical_agent(ticker)
    print(tech_result)

    print(f"\n[AGENT 3 — Chief Analyst — FINAL VERDICT]")
    final = run_chief_agent(ticker, fund_result, tech_result)
    print(final)

# ─── Main Loop ─────────────────────────────────────────────────
print("=== Full Autonomous 3-Agent Stock Research Pipeline ===\n")
print("Note: Use NSE format — INFY.NS / TCS.NS / RELIANCE.NS\n")

while True:
    ticker = input("Enter stock ticker (or 'exit'): ").strip().upper()
    if ticker.lower() == 'exit':
        print("Exiting. Goodbye!")
        break
    run_full_pipeline(ticker)
    print("\n" + "="*50 + "\n")