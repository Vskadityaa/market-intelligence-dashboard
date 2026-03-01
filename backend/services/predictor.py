"""Stock trend and simple prediction from historical data."""
from __future__ import annotations

from typing import Any, Optional
import yfinance as yf

from services.stock_service import _symbol_for_exchange


def get_trend_and_prediction(symbol: str, exchange: str = "us") -> dict[str, Any]:
    """
    Compute short-term trend from recent price history.
    exchange: us, nse, bse (uses Yahoo Finance with .NS/.BO suffix).
    """
    symbol_raw = (symbol or "").upper().strip()
    yf_symbol = _symbol_for_exchange(symbol_raw, exchange or "us")
    try:
        t = yf.Ticker(yf_symbol)
        hist = t.history(period="3mo")
        if hist is None or hist.empty or len(hist) < 5:
            return {
                "symbol": symbol_raw,
                "trend_5d_pct": None,
                "trend_20d_pct": None,
                "trend_direction": "unknown",
                "current_price": None,
                "prediction_note": "Not enough history for trend.",
                "support_resistance_note": None,
            }
        close = hist["Close"]
        current = float(close.iloc[-1])
        n = len(close)
        price_5d_ago = float(close.iloc[-5]) if n >= 5 else current
        price_20d_ago = float(close.iloc[-min(20, n)]) if n >= 2 else current
        trend_5d = ((current - price_5d_ago) / price_5d_ago * 100) if price_5d_ago else None
        trend_20d = ((current - price_20d_ago) / price_20d_ago * 100) if price_20d_ago else None

        if trend_5d is not None and trend_20d is not None:
            if trend_5d > 1 and trend_20d > 1:
                direction = "up"
                note = f"Short-term momentum is positive: +{trend_5d:.1f}% over 5 days and +{trend_20d:.1f}% over 20 days. Trend suggests continued strength if volume supports."
            elif trend_5d < -1 and trend_20d < -1:
                direction = "down"
                note = f"Stock has been under pressure: {trend_5d:.1f}% over 5 days and {trend_20d:.1f}% over 20 days. Watch for support levels before adding."
            elif trend_5d > trend_20d:
                direction = "improving"
                note = f"Recent improvement: 5-day return ({trend_5d:.1f}%) is better than 20-day ({trend_20d:.1f}%). Could be early recovery."
            else:
                direction = "sideways"
                note = f"Mixed signals: 5-day {trend_5d:.1f}%, 20-day {trend_20d:.1f}%. Wait for clearer direction."
        else:
            direction = "unknown"
            note = "Insufficient data for trend prediction."

        # Simple support/resistance from recent high/low
        recent_high = float(close.max())
        recent_low = float(close.min())
        support_resistance = f"Recent range: ${recent_low:.2f}–${recent_high:.2f}. Price near high may face resistance; near low may find support."

        return {
            "symbol": symbol_raw,
            "trend_5d_pct": round(trend_5d, 2) if trend_5d is not None else None,
            "trend_20d_pct": round(trend_20d, 2) if trend_20d is not None else None,
            "trend_direction": direction,
            "current_price": current,
            "prediction_note": note,
            "support_resistance_note": support_resistance,
        }
    except Exception as e:
        return {
            "symbol": symbol_raw,
            "trend_5d_pct": None,
            "trend_20d_pct": None,
            "trend_direction": "error",
            "current_price": None,
            "prediction_note": str(e),
            "support_resistance_note": None,
        }
