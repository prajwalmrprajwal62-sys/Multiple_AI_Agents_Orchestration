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
    "Technology": {"typical_pe_range": "22-30", "note": "IT services sector, India (approximate reference, not live-calculated)"},
    "Financial Services": {"typical_pe_range": "15-22", "note": "Banking/NBFC sector, India (approximate reference)"},
    "Consumer Cyclical": {"typical_pe_range": "25-40", "note": "Auto, retail sector, India (approximate reference)"},
    "Healthcare": {"typical_pe_range": "25-35", "note": "Pharma sector, India (approximate reference)"},
    "Consumer Defensive": {"typical_pe_range": "40-60", "note": "FMCG sector, India (approximate reference)"},
    "Energy": {"typical_pe_range": "10-18", "note": "Oil & gas, energy sector, India (approximate reference)"},
    "Basic Materials": {"typical_pe_range": "12-20", "note": "Metals, cement, chemicals, India (approximate reference)"},
    "Industrials": {"typical_pe_range": "20-30", "note": "Capital goods, EMS sector, India (approximate reference)"},
    "Communication Services": {"typical_pe_range": "18-28", "note": "Telecom, media, India (approximate reference)"},
}

def sanitize(data: dict) -> dict:
    """Replaces NaN/None/infinite values with 'N/A' so the data is always valid JSON before it's sent to the API."""
    clean = {}
    for key, value in data.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            clean[key] = "N/A"
        elif value is None:
            clean[key] = "N/A"
        else:
            clean[key] = value
    return clean

def get_fundamental_data(ticker: str) -> dict:
    """Fetches fundamental financial data for an Indian stock (PE ratio, ROE, profit margins, debt, revenue growth, sector). Use when the user asks about valuation, profitability, or long-term investment quality. Ticker must use .NS suffix, e.g. INFY.NS."""
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
    """Fetches technical price data for an Indian stock (current price, moving averages, 52-week range). Use when the user asks about price trends, momentum, or short-term outlook. Ticker must use .NS suffix, e.g. INFY.NS."""
    stock = yf.Ticker(ticker)
    try:
        info = stock.info
        history = stock.history(period="3mo")
    except Exception as exc:
        raise RuntimeError(f"yfinance could not fetch technical data for {ticker}.") from exc

    if history.empty:
        raise RuntimeError(f"No price history for {ticker}. Check the ticker symbol.")

    valid_closes = history["Close"].dropna()
    if not valid_closes.empty:
        current_price = round(valid_closes.iloc[-1], 2)
    else:
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"

    return sanitize({
        "Current Price": current_price,
        "50 Day MA": info.get("fiftyDayAverage", "N/A"),
        "200 Day MA": info.get("twoHundredDayAverage", "N/A"),
        "52W High": info.get("fiftyTwoWeekHigh", "N/A"),
        "52W Low": info.get("fiftyTwoWeekLow", "N/A"),
    })

def get_industry_benchmark(sector: str) -> dict:
    """Returns a typical PE ratio range for a given market sector in the Indian stock market, used to judge whether a stock's PE is high or low relative to peers. Call this AFTER get_fundamental_data, passing the exact 'Sector' value it returned. This is a static approximate reference table, not live-calculated data — state that clearly when using it. Available sectors: Technology, Financial Services, Consumer Cyclical, Healthcare, Consumer Defensive, Energy, Basic Materials, Industrials, Communication Services."""
    data = INDUSTRY_PE_BENCHMARKS.get(sector)
    if not data:
        return {"error": f"No benchmark available for sector '{sector}'. Say comparison isn't possible instead of guessing a number."}
    return data

def ask_agent_with_tools(user_message, max_retries=2):
    system_instruction = (
        "You are a stock research assistant for Indian markets (tickers use .NS suffix). "
        "Decide which tools you need based on the user's question and call them. "
        "If judging valuation (like PE ratio), you MUST call get_fundamental_data first to "
        "get the sector, then call get_industry_benchmark with that sector before giving an opinion. "
        "Clearly separate VERIFIED data (from tools) from ESTIMATED/REFERENCE data (like the industry "
        "benchmark, which is approximate, not live-calculated) — say so explicitly in your answer. "
        "Never invent numbers you don't have. Be concise."
    )

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[get_fundamental_data, get_technical_data, get_industry_benchmark],
                ),
            )
            return response.text
        except Exception as e:
            err_text = str(e).lower()
            transient = ("429" in err_text or "resource_exhausted" in err_text or "quota" in err_text
                         or "503" in err_text or "unavailable" in err_text)
            if transient:
                if attempt < max_retries:
                    wait_time = 15 * (attempt + 1)
                    print(f"Server busy/rate limited. Waiting {wait_time}s before retry ({attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    return "Server still unavailable after retries. This is usually temporary — try again in a minute."
            else:
                return f"Unexpected error: {e}"

print("=== Agent With Tools + Industry Benchmarking (Sanitized + Robust Price Fetch) ===\n")
print("Note: Use NSE format — INFY.NS / TCS.NS / RELIANCE.NS\n")

while True:
    query = input("Ask anything about a stock (or 'exit'): ").strip()
    if query.lower() == 'exit':
        print("Exiting. Goodbye!")
        break

    result = ask_agent_with_tools(query)
    print(f"\n{result}\n")
    print("="*50 + "\n")