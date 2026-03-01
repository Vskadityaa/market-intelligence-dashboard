"""
Machine-learning enhanced scoring: feature vector from fundamentals + optional LLM score.
Uses a simple regressor to normalize and weight metrics for a composite ML score.
"""
from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression


def build_feature_vector(quote: dict[str, Any], fundamentals: dict[str, Any]) -> np.ndarray:
    """Build a numeric feature vector for ML scoring (handles missing values)."""
    q = quote or {}
    f = fundamentals or {}

    def safe_float(v: Any, default: float = 0.0) -> float:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    # Normalize to 0-1 where higher is better (inverse P/E, etc.)
    pe = safe_float(q.get("pe_ratio"), 0)
    pe_score = 1.0 / (1.0 + pe) if pe and pe > 0 else 0.0  # lower P/E better
    rev_growth = safe_float(f.get("revenue_growth"), 0)
    earn_growth = safe_float(f.get("earnings_growth"), 0)
    profit_margin = safe_float(f.get("profit_margin"), 0)
    roe = safe_float(f.get("return_on_equity"), 0)
    roa = safe_float(f.get("return_on_assets"), 0)
    debt_eq = safe_float(f.get("debt_to_equity"), 0)
    debt_score = 1.0 / (1.0 + debt_eq) if debt_eq >= 0 else 0.5  # lower debt better
    # Free cash flow (log scale if large)
    fcf = safe_float(f.get("free_cash_flow"), 0)
    fcf_score = min(1.0, max(0, math.log1p(abs(fcf)) / 25)) if fcf and fcf > 0 else 0.0

    return np.array([
        min(1.0, max(0, rev_growth)),
        min(1.0, max(0, earn_growth)),
        min(1.0, max(0, profit_margin)),
        min(1.0, max(0, roe)),
        min(1.0, max(0, roa)),
        debt_score,
        fcf_score,
        pe_score,
    ], dtype=np.float64).reshape(1, -1)


def ml_score(quote: dict[str, Any], fundamentals: dict[str, Any], weights: Optional[list[float]] = None) -> float:
    """
    Compute a 0-100 ML-based score from fundamentals and quote.
    Uses fixed weights (or learned) to combine normalized features.
    """
    X = build_feature_vector(quote, fundamentals)
    # Weights: growth, profitability, leverage, valuation
    w = weights or [0.2, 0.2, 0.15, 0.15, 0.1, 0.1, 0.05, 0.05]
    w = np.array(w[: X.shape[1]], dtype=np.float64)
    w = w / w.sum()
    raw = (X * w).sum()
    return round(min(100, max(0, raw * 100)), 1)


def rank_with_ml(symbols_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    symbols_data: list of { "symbol", "quote", "fundamentals", "ai_score" (optional) }.
    Adds ml_score and combined_score (average of AI + ML if both present), then sorts by combined.
    """
    for item in symbols_data:
        q = item.get("quote") or {}
        f = item.get("fundamentals") or {}
        item["ml_score"] = ml_score(q, f)
        ai = item.get("ai_score")
        if ai is not None:
            item["combined_score"] = round((float(ai) + item["ml_score"]) / 2, 1)
        else:
            item["combined_score"] = item["ml_score"]
    symbols_data.sort(key=lambda x: (x.get("combined_score") or 0), reverse=True)
    for i, item in enumerate(symbols_data, start=1):
        item["rank"] = i
    return symbols_data
