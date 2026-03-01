"""
Market Intelligence Dashboard - FastAPI backend.
Endpoints: search, quotes, fundamentals, earnings transcript, AI summary, AI Score, compare all.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_settings
from utils import sanitize_for_json
from services.stock_service import (
    get_quote,
    get_fundamentals,
    search_symbols,
    get_multiple_quotes,
    SUPPORTED_EXCHANGES,
)
from services.earnings_service import get_earnings_transcript, list_earnings_dates
from services.llm_service import summarize_earnings_transcript, compute_ai_score, get_ai_analysis_and_hints
from services.ml_scorer import rank_with_ml, ml_score
from services.predictor import get_trend_and_prediction


# ---------- Pydantic models ----------
class SearchResult(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = "us"


class CompareRequest(BaseModel):
    symbols: list[str]
    exchange: Optional[str] = "us"


# ---------- Scheduler for periodic refresh ----------
def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    # Placeholder: in production, refresh cache or re-fetch top symbols periodically
    scheduler = BackgroundScheduler()
    # scheduler.add_job(refresh_cache, 'interval', hours=6)
    scheduler.start()
    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # start_scheduler()  # enable when cache is implemented
    yield
    # shutdown


app = FastAPI(
    title="Market Intelligence Dashboard API",
    description="Stock search, fundamentals, earnings transcripts, AI summarization, and AI/ML ranking.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    """Return JSON error for any uncaught exception so frontend gets a message."""
    from fastapi.responses import JSONResponse
    from fastapi import HTTPException as FastAPIHTTPException
    if isinstance(exc, FastAPIHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error": "Internal Server Error"},
    )


# ---------- Routes ----------
@app.get("/")
def root():
    return {"service": "Market Intelligence Dashboard API", "docs": "/docs"}


@app.get("/api/exchanges")
def list_exchanges():
    """List supported data sources: us (US stocks), nse (NSE India), bse (BSE India)."""
    return {"exchanges": SUPPORTED_EXCHANGES, "description": "us = US (Yahoo), nse = NSE India, bse = BSE India"}


@app.get("/api/search", response_model=list[SearchResult])
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    exchange: Optional[str] = Query(None, description="Filter: us, nse, bse or omit for all"),
):
    """Search symbols by ticker or name. Optional exchange filter (us, nse, bse)."""
    try:
        results = search_symbols(q, limit=limit, exchange=exchange)
        return [SearchResult(symbol=r["symbol"], name=r.get("name") or r["symbol"], exchange=r.get("exchange") or "us") for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quote/{symbol}")
def quote(symbol: str, exchange: str = Query("us", description="us, nse, bse")):
    """Get current quote. Use exchange=nse for NSE India, exchange=bse for BSE."""
    try:
        return sanitize_for_json(get_quote(symbol, exchange=exchange))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fundamentals/{symbol}")
def fundamentals(symbol: str, exchange: str = Query("us", description="us, nse, bse")):
    """Get fundamental financial data. Use exchange=nse or bse for Indian stocks."""
    try:
        return sanitize_for_json(get_fundamentals(symbol, exchange=exchange))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quote/batch")
def batch_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    exchange: str = Query("us", description="us, nse, bse"),
):
    """Get quotes for multiple symbols. Use exchange=nse or bse for Indian stocks."""
    try:
        sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
        return sanitize_for_json(get_multiple_quotes(sym_list, exchange=exchange))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/earnings/transcript/{symbol}")
def earnings_transcript(
    symbol: str,
    year: Optional[int] = Query(None),
    quarter: Optional[int] = Query(None),
):
    """Fetch earnings call transcript (requires FMP_API_KEY)."""
    try:
        return sanitize_for_json(get_earnings_transcript(symbol, year=year, quarter=quarter))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/earnings/dates/{symbol}")
def earnings_dates(symbol: str):
    """List available earnings dates for a symbol."""
    try:
        return list_earnings_dates(symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/earnings/summary/{symbol}")
def earnings_summary(
  symbol: str,
  year: Optional[int] = Query(None),
  quarter: Optional[int] = Query(None),
):
  """
  Get earnings transcript and AI-generated summary (requires FMP_API_KEY + OPENAI_API_KEY).
  """
  try:
    data = get_earnings_transcript(symbol, year=year, quarter=quarter)
    if not data.get("available") or not data.get("transcript_text"):
      return sanitize_for_json(data)
    summary_result = summarize_earnings_transcript(
      data["transcript_text"],
      symbol=data["symbol"],
    )
    data["ai_summary"] = summary_result.get("summary")
    data["highlights"] = summary_result.get("highlights", [])
    data["sentiment"] = summary_result.get("sentiment")
    data["key_metrics"] = summary_result.get("key_metrics", [])
    return sanitize_for_json(data)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/score/{symbol}")
def ai_score(symbol: str, exchange: str = Query("us", description="us, nse, bse")):
  """Get AI Score and ML score. Use exchange=nse or bse for Indian stocks."""
  try:
    quote_data = get_quote(symbol, exchange=exchange)
    if quote_data.get("error"):
      raise HTTPException(status_code=404, detail=quote_data["error"])
    fund_data = get_fundamentals(symbol, exchange=exchange)
    sentiment = None
    result = {
      "symbol": symbol,
      "quote": sanitize_for_json(quote_data),
      "fundamentals": sanitize_for_json(fund_data),
      "ai_score": None,
      "ml_score": ml_score(quote_data, fund_data),
      "rationale": None,
      "rank": None,
    }
    ai = compute_ai_score(symbol, fund_data, quote_data, summary_sentiment=sentiment)
    result["ai_score"] = ai.get("ai_score")
    result["rationale"] = ai.get("rationale")
    return sanitize_for_json(result)
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analyze/{symbol}")
def analyze_stock(symbol: str, exchange: str = Query("us", description="us, nse, bse")):
  """AI prediction, analysis, and hints. Use exchange=nse or bse for Indian stocks."""
  try:
    quote_data = get_quote(symbol, exchange=exchange)
    if quote_data.get("error"):
      raise HTTPException(status_code=404, detail=quote_data["error"])
    fund_data = get_fundamentals(symbol, exchange=exchange)
    trend_data = get_trend_and_prediction(symbol, exchange=exchange)
    earnings_sentiment = None
    try:
      transcript = get_earnings_transcript(symbol)
      if transcript.get("available") and transcript.get("transcript_text"):
        summary = summarize_earnings_transcript(transcript["transcript_text"], symbol, max_tokens=400)
        earnings_sentiment = summary.get("sentiment")
    except Exception:
      pass
    ai_analysis = get_ai_analysis_and_hints(
      symbol,
      quote_data,
      fund_data,
      trend_data,
      earnings_sentiment=earnings_sentiment,
    )
    out = {
      "symbol": symbol,
      "quote": sanitize_for_json(quote_data),
      "trend": sanitize_for_json(trend_data),
      "prediction_note": trend_data.get("prediction_note"),
      "support_resistance": trend_data.get("support_resistance_note"),
      "analysis": ai_analysis.get("analysis"),
      "prediction_outlook": ai_analysis.get("prediction_outlook"),
      "hints": ai_analysis.get("hints") or [],
      "error": ai_analysis.get("error"),
    }
    return sanitize_for_json(out)
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare")
def compare_all(body: CompareRequest):
  """Compare symbols (quotes, fundamentals, AI/ML score, rank). Body may include exchange: us, nse, bse."""
  try:
    symbols = [s.upper().strip() for s in (body.symbols or []) if s.strip()]
    if not symbols:
      raise HTTPException(status_code=400, detail="Provide at least one symbol.")
    if len(symbols) > 30:
      symbols = symbols[:30]
    exchange = (body.exchange or "us").lower() if hasattr(body, "exchange") else "us"

    out = []
    for sym in symbols:
      q = get_quote(sym, exchange=exchange)
      f = get_fundamentals(sym, exchange=exchange)
      if q.get("error"):
        continue
      ai = compute_ai_score(sym, f, q, summary_sentiment=None)
      out.append({
        "symbol": sym,
        "quote": q,
        "fundamentals": f,
        "ai_score": ai.get("ai_score"),
        "rationale": ai.get("rationale"),
        "ml_score": None,
        "combined_score": None,
        "rank": None,
      })

    for item in out:
      item["ml_score"] = ml_score(item["quote"], item["fundamentals"])
      ai = item.get("ai_score")
      item["combined_score"] = round((float(ai or 0) + item["ml_score"]) / 2, 1) if ai is not None else item["ml_score"]

    out.sort(key=lambda x: x["combined_score"], reverse=True)
    for i, item in enumerate(out, start=1):
      item["rank"] = i

    return sanitize_for_json({"symbols": out, "count": len(out)})
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health():
  return {"status": "ok"}


if __name__ == "__main__":
  import uvicorn
  s = get_settings()
  # Run without reload to avoid restarts from venv/__pycache__ changes
  uvicorn.run("main:app", host=s.host, port=s.port)
