"""Earnings call transcript fetching and storage."""
from __future__ import annotations

from typing import Any, Optional
import httpx

from config import get_settings


def get_earnings_transcript(symbol: str, year: Optional[int] = None, quarter: Optional[int] = None) -> dict[str, Any]:
    """
    Fetch earnings call transcript for a symbol.
    Uses FMP if API key is set; otherwise returns placeholder with instructions.
    """
    symbol = (symbol or "").upper().strip()
    settings = get_settings()

    if settings.fmp_api_key:
        return _fetch_fmp_transcript(symbol, year, quarter)

    return {
        "symbol": symbol,
        "available": False,
        "message": "Earnings transcripts require FMP API key. Set FMP_API_KEY in .env. See .env.example.",
        "transcript_text": None,
        "date": None,
        "quarter": None,
        "year": None,
    }


def _fetch_fmp_transcript(symbol: str, year: Optional[int], quarter: Optional[int]) -> dict[str, Any]:
    """Fetch transcript from Financial Modeling Prep."""
    settings = get_settings()
    # FMP: earning call transcript endpoint
    url = (
        f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{symbol}"
        f"?apikey={settings.fmp_api_key}"
    )
    if year is not None:
        url += f"&year={year}"
    if quarter is not None:
        url += f"&quarter={quarter}"

    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url)
            if r.status_code != 200:
                return {
                    "symbol": symbol,
                    "available": False,
                    "message": f"API error: {r.status_code}",
                    "transcript_text": None,
                    "date": None,
                    "quarter": None,
                    "year": None,
                }
            data = r.json()
            if not data or not isinstance(data, list):
                return {
                    "symbol": symbol,
                    "available": False,
                    "message": "No transcript found for this period.",
                    "transcript_text": None,
                    "date": None,
                    "quarter": None,
                    "year": None,
                }
            item = data[0]
            content = item.get("content") or item.get("transcript") or ""
            return {
                "symbol": symbol,
                "available": True,
                "transcript_text": content,
                "date": item.get("date"),
                "quarter": item.get("quarter"),
                "year": item.get("year"),
                "message": None,
            }
    except Exception as e:
        return {
            "symbol": symbol,
            "available": False,
            "message": str(e),
            "transcript_text": None,
            "date": None,
            "quarter": None,
            "year": None,
        }


def list_earnings_dates(symbol: str) -> list[dict[str, Any]]:
    """List available earnings dates/quarters for a symbol (FMP)."""
    symbol = (symbol or "").upper().strip()
    settings = get_settings()
    if not settings.fmp_api_key:
        return []

    url = (
        f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{symbol}"
        f"?apikey={settings.fmp_api_key}"
    )
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url)
            if r.status_code != 200:
                return []
            data = r.json()
            if not isinstance(data, list):
                return []
            return [
                {
                    "date": item.get("date"),
                    "quarter": item.get("quarter"),
                    "year": item.get("year"),
                }
                for item in data[:12]
            ]
    except Exception:
        return []
