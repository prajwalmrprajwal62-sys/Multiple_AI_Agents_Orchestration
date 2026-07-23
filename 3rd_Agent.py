import os
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

# ─── Fetch Real Stock Data ───────────────────────────────
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)

    try:
        info = stock.info
        history = stock.history(period="3mo")
    except Exception as exc:
        raise RuntimeError(
            f"yfinance could not fetch data for {ticker}. This usually means the ticker is invalid, data is unavailable, or Yahoo Finance is rate-limiting requests."
        ) from exc

    if history.empty:
        raise RuntimeError(
            f"yfinance returned no price history for {ticker}. Check the ticker symbol, network connection, or Yahoo Finance availability."
        )

    fundamental = {
        "Company"        : info.get("longName", "N/A"),
        "Market Cap"     : info.get("marketCap", "N/A"),
        "PE Ratio"       : info.get("trailingPE", "N/A"),
        "ROE"            : info.get("returnOnEquity", "N/A"),
        "Profit Margins" : info.get("profitMargins", "N/A"),
        "Revenue Growth" : info.get("revenueGrowth", "N/A"),
        "Debt to Equity" : info.get("debtToEquity", "N/A"),
    }

    technical = {
        "Current Price" : round(history["Close"].iloc[-1], 2),
        "52W High"      : info.get("fiftyTwoWeekHigh", "N/A"),
        "52W Low"       : info.get("fiftyTwoWeekLow", "N/A"),
        "50 Day MA"     : info.get("fiftyDayAverage", "N/A"),
        "200 Day MA"    : info.get("twoHundredDayAverage", "N/A"),
        "Avg Volume"    : info.get("averageVolume", "N/A"),
    }

    return fundamental, technical

# ─── Ask Agent ───────────────────────────────────────────
def ask_agent(system_instruction, user_message):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction
        ),
    )
    return response.text

# ─── Agent Roles ─────────────────────────────────────────
FUNDAMENTAL_ANALYST = "You are a fundamental analyst for Indian stocks. You are given real financial data. Analyze it and give a clear buy/hold/sell opinion with reasoning. Be concise."

TECHNICAL_ANALYST = "You are a technical analyst for Indian stocks. You are given real price data. Analyze trends, moving averages, momentum and give a short-term outlook. Be concise."

# NEW — The Manager Agent
CHIEF_ANALYST = "You are a chief investment analyst. You are given a fundamental analysis AND a technical analysis of the same stock, written by two junior analysts. Your job is to weigh both, resolve any conflict between them, and give ONE final verdict: BUY, HOLD, or SELL — with a 3-4 line justification. Be decisive, not vague."

# ─── Main Loop ───────────────────────────────────────────
print("=== Multi Agent Stock Research (Real Data + Final Verdict) ===\n")
print("Note: Use NSE format — INFY.NS / TCS.NS / RELIANCE.NS\n")

while True:
    ticker = input("Enter stock ticker (or 'exit' to quit): ").strip().upper()
    if ticker.lower() == 'exit':
        break

    print(f"\nFetching real data for {ticker}...")
    try:
        fundamental_data, technical_data = get_stock_data(ticker)

        print(f"\n[AGENT 1 — Fundamental Analysis]")
        fund_result = ask_agent(
            FUNDAMENTAL_ANALYST,
            f"Here is the real financial data for {ticker}: {fundamental_data}. Analyze this."
        )
        print(fund_result)

        print(f"\n[AGENT 2 — Technical Analysis]")
        tech_result = ask_agent(
            TECHNICAL_ANALYST,
            f"Here is the real price data for {ticker}: {technical_data}. Analyze this."
        )
        print(tech_result)

        # ── NEW PART — Agent 3 reads Agent 1 + Agent 2's output ──
        print(f"\n[AGENT 3 — Chief Analyst — FINAL VERDICT]")
        combined_input = f"""
        Fundamental Analysis:
        {fund_result}

        Technical Analysis:
        {tech_result}

        Give your final verdict on {ticker}.
        """
        final_verdict = ask_agent(CHIEF_ANALYST, combined_input)
        print(final_verdict)

        print("\n" + "="*50 + "\n")

    except RuntimeError as e:
        print(f"Data error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")