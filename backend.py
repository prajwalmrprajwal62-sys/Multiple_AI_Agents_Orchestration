# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# import your existing pipeline functions
from pipeline import get_cached_or_run  # your cache-wrapped pipeline function

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your actual Vercel URL once deployed
    allow_methods=["*"],
    allow_headers=["*"],
)

class TickerRequest(BaseModel):
    ticker: str

@app.post("/analyze")
def analyze(request: TickerRequest):
    ticker = request.ticker.strip().upper()
    result = get_cached_or_run(ticker)
    return result

@app.get("/")
def health_check():
    return {"status": "running"}