import os
import yfinance as yf
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
client = genai.Client(api_key=API_KEY)

# ─── Tools — plain Python functions, model will call these ITSELF ───
def get_fundamental_data(ticker: str) -> dict:
    """Fetches fundamental financial data for a given stock ticker (PE ratio, ROE, profit margins, debt, revenue growth). Use this when the user asks about company financials, valuation, profitability, or long-term investment quality."""
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "Company": info.get("longName", "N/A"),
        "PE Ratio": info.get("trailingPE", "N/A"),
        "ROE": info.get("returnOnEquity", "N/A"),
        "Profit Margins": info.get("profitMargins", "N/A"),
        "Revenue Growth": info.get("revenueGrowth", "N/A"),
        "Debt to Equity": info.get("debtToEquity", "N/A"),
    }

def get_technical_data(ticker: str) -> dict:
    """Fetches technical price data for a given stock ticker (current price, moving averages, 52-week range). Use this when the user asks about price trends, momentum, or short-term trading outlook."""
    stock = yf.Ticker(ticker)
    info = stock.info
    history = stock.history(period="3mo")
    return {
        "Current Price": round(history["Close"].iloc[-1], 2),
        "50 Day MA": info.get("fiftyDayAverage", "N/A"),
        "200 Day MA": info.get("twoHundredDayAverage", "N/A"),
        "52W High": info.get("fiftyTwoWeekHigh", "N/A"),
        "52W Low": info.get("fiftyTwoWeekLow", "N/A"),
    }

# ─── Agent with tools — model decides what to call ───
def ask_agent_with_tools(user_message):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=(
                "... After using tool data, if a full verdict requires comparison to industry "
             "norms (e.g. is PE overvalued), use your general knowledge of typical Indian IT "
             "sector PE ranges to give a reasoned opinion — but explicitly state when you're "
             "supplementing tool data with general knowledge, so it's clear what's verified vs estimated."
            ),
            tools=[get_fundamental_data, get_technical_data],
        ),
    )
    return response.text

# ─── Test it — notice you're NOT telling it which function to call ───
print("=== Agent With Tools — Model Decides ===\n")

while True:
    query = input("Ask anything about a stock (or 'exit'): ").strip()
    if query.lower() == 'exit':
        break
    result = ask_agent_with_tools(query)
    print(f"\n{result}\n")