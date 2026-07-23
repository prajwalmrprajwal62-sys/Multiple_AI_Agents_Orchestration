import os

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if not API_KEY:
    raise EnvironmentError("Set GEMINI_API_KEY in your environment before running this script.")

client = genai.Client(api_key=API_KEY)

def ask_agent(system_instruction, user_message):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )
    return response.text

Fundamental_ANALYST ="You are a financial analyst who specializes in Indian stock markets. Analyze revenue,profit margins, growth potential,dept,ROE and competitive position of the company.BE concise and clear."
Technical_ANALYST = "You are a technical analyst who specializes in Indian stock markets. Analyze the stock's price trends, support and resistance levels, moving averages,short-term outlook and momentum indicators. Provide insights on potential entry and exit points for traders. Be concise and clear."


print("=== Multi Agent System for Stock Analysis ===")

while True:
    stock= input("Enter the stock symbol (or 'exit' to quit): ").strip()
    if stock.lower() == 'exit':
        print("Exiting the system. Goodbye!")
        break

    print(f"\n[AGENT 1--- Fundamental Analysis OF {stock} ---]")
    fundamental_result = ask_agent(Fundamental_ANALYST, f"Provide a fundamental analysis of {stock}")
    print(fundamental_result)

    print(f"\n[AGENT 2--- Technical Analysis OF {stock} ---]")
    technical_result = ask_agent(Technical_ANALYST, f"Provide a technical analysis of {stock}")
    print(technical_result)

    print("\n" + "="*50 + "\n")