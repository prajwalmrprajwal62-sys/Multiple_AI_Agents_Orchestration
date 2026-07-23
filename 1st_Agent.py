import os

from google import genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if not API_KEY:
    raise EnvironmentError("Set GEMINI_API_KEY in your environment before running this script.")

client = genai.Client(api_key=API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a financial analyst who specializes in Indian stock markets. "
    "Be concise and clear."
)

def ask_agent(user_message):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config={"system_instruction": SYSTEM_INSTRUCTION},
    )
    return response.text

# Test it
result = ask_agent("Give me a brief fundamental analysis of Infosys as a company.")
print(result)