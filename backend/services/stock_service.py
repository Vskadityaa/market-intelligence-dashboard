"""Stock data service: quotes, fundamentals, and multi-source support.
Supports: US (Yahoo), NSE India (.NS), BSE India (.BO). Optional nsetools for direct NSE."""
from __future__ import annotations

import os
from typing import Any, Optional
import yfinance as yf
import pandas as pd
import httpx

from config import get_settings

# Exchange suffixes for Yahoo Finance (works globally)
EXCHANGE_SUFFIX = {"us": "", "nse": ".NS", "bse": ".BO"}
SUPPORTED_EXCHANGES = list(EXCHANGE_SUFFIX.keys())


def _symbol_for_exchange(symbol: str, exchange: str) -> str:
    """Return symbol string for the given exchange (e.g. RELIANCE.NS for NSE)."""
    symbol = (symbol or "").upper().strip()
    suf = EXCHANGE_SUFFIX.get((exchange or "us").lower(), "")
    if suf and not symbol.endswith(suf):
        return symbol + suf
    return symbol


def get_quote(symbol: str, exchange: str = "us") -> dict[str, Any]:
    """Get current quote. exchange: us, nse, bse. Uses Yahoo Finance (and optional nsetools for NSE)."""
    symbol_raw = (symbol or "").upper().strip()
    if exchange and exchange.lower() == "nse":
        q = _get_quote_nse_fallback(symbol_raw)
        if q:
            return q
    yf_symbol = _symbol_for_exchange(symbol_raw, exchange or "us")
    t = yf.Ticker(yf_symbol)
    try:
        info = t.info
        hist = t.history(period="1mo")
        fast = t.fast_info if hasattr(t, "fast_info") else None
    except Exception as e:
        return {"error": str(e), "symbol": symbol_raw, "exchange": exchange or "us"}

    last_close = None
    if hist is not None and not hist.empty:
        last_close = float(hist["Close"].iloc[-1])

    return {
        "symbol": symbol_raw,
        "exchange": exchange or "us",
        "name": info.get("shortName") or info.get("longName") or symbol_raw,
        "price": info.get("currentPrice") or last_close or info.get("regularMarketPrice"),
        "previous_close": info.get("previousClose"),
        "change": info.get("regularMarketChange"),
        "change_percent": info.get("regularMarketChangePercent"),
        "volume": info.get("volume") or info.get("regularMarketVolume"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio"),
        "price_to_book": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "52_week_high": info.get("fiftyTwoWeekHigh"),
        "52_week_low": info.get("fiftyTwoWeekLow"),
        "avg_volume": info.get("averageVolume"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }


def _get_quote_nse_fallback(symbol: str) -> Optional[dict[str, Any]]:
    """Try direct NSE via nsetools if available; else return None (caller uses yfinance .NS)."""
    try:
        from nsetools import Nse
        nse = Nse()
        q = nse.get_quote(symbol)
        if q and isinstance(q, dict) and q.get("symbol"):
            return {
                "symbol": (q.get("symbol") or symbol).upper(),
                "exchange": "nse",
                "name": q.get("companyName") or q.get("symbol") or symbol,
                "price": _safe_num(q.get("lastPrice") or q.get("basePrice")),
                "previous_close": _safe_num(q.get("previousClose") or q.get("basePrice")),
                "change": _safe_num(q.get("change")),
                "change_percent": _safe_num(q.get("pChange")) and (float(q.get("pChange", 0)) / 100),
                "volume": _safe_num(q.get("totalTradedVolume") or q.get("quantityTraded")),
                "market_cap": _safe_num(q.get("marketCap")) or _safe_num(q.get("totalTradedValue")),
                "52_week_high": _safe_num(q.get("high52") or q.get("dayHigh")),
                "52_week_low": _safe_num(q.get("low52") or q.get("dayLow")),
                "sector": None,
                "industry": None,
            }
    except Exception:
        pass
    return None


def get_fundamentals(symbol: str, exchange: str = "us") -> dict[str, Any]:
    """Get fundamental financial data. exchange: us, nse, bse."""
    symbol_raw = (symbol or "").upper().strip()
    yf_symbol = _symbol_for_exchange(symbol_raw, exchange or "us")
    t = yf.Ticker(yf_symbol)
    try:
        info = t.info
        inc = t.income_stmt
        bal = t.balance_sheet
        cf = t.cashflow
        earnings = t.earnings if hasattr(t, "earnings") else None
    except Exception as e:
        return {"error": str(e), "symbol": symbol_raw, "exchange": exchange or "us"}

    # Latest annual income statement
    revenue = net_income = gross_profit = operating_income = None
    if inc is not None and not inc.empty:
        row = inc.iloc[:, 0] if inc.shape[1] > 0 else inc.iloc[0]
        revenue = _safe_num(row.get("Total Revenue") or row.get("Revenue"))
        net_income = _safe_num(row.get("Net Income") or row.get("Net Income Common Stockholders"))
        gross_profit = _safe_num(row.get("Gross Profit"))
        operating_income = _safe_num(row.get("Operating Income") or row.get("EBIT"))

    # Balance sheet
    total_assets = total_equity = total_debt = None
    if bal is not None and not bal.empty:
        row = bal.iloc[:, 0] if bal.shape[1] > 0 else bal.iloc[0]
        total_assets = _safe_num(row.get("Total Assets"))
        total_equity = _safe_num(row.get("Stockholders Equity") or row.get("Total Equity Gross Minority Interest"))
        total_debt = _safe_num(row.get("Total Debt"))

    # Cash flow
    operating_cf = free_cf = None
    if cf is not None and not cf.empty:
        row = cf.iloc[:, 0] if cf.shape[1] > 0 else cf.iloc[0]
        operating_cf = _safe_num(row.get("Operating Cash Flow") or row.get("Cash Flow From Continuing Operating Activities"))
        free_cf = _safe_num(row.get("Free Cash Flow"))

    # Growth indicators from info
    revenue_growth = info.get("revenueGrowth")
    earnings_growth = info.get("earningsGrowth")
    profit_margin = info.get("profitMargins")
    operating_margin = info.get("operatingMargins")
    roe = info.get("returnOnEquity")
    roa = info.get("returnOnAssets")
    debt_to_equity = info.get("debtToEquity")

    return {
        "symbol": symbol_raw,
        "exchange": exchange or "us",
        "revenue": revenue,
        "net_income": net_income,
        "gross_profit": gross_profit,
        "operating_income": operating_income,
        "total_assets": total_assets,
        "total_equity": total_equity,
        "total_debt": total_debt,
        "operating_cash_flow": operating_cf,
        "free_cash_flow": free_cf,
        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
        "profit_margin": profit_margin,
        "operating_margin": operating_margin,
        "return_on_equity": roe,
        "return_on_assets": roa,
        "debt_to_equity": debt_to_equity,
        "earnings_dates": _earnings_dates(t),
    }


def _safe_num(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _earnings_dates(t) -> Optional[list[dict]]:
    try:
        ed = t.get_earnings_dates()
        if ed is None or ed.empty:
            return None
        ed = ed.head(12)
        return [
            {"date": str(idx.date()) if hasattr(idx, "date") else str(idx), "eps_estimate": _safe_num(row.get("EPS Estimate")), "reported": _safe_num(row.get("Reported EPS"))}
            for idx, row in ed.iterrows()
        ]
    except Exception:
        return None


def search_symbols(query: str, limit: int = 20, exchange: Optional[str] = None) -> list[dict[str, Any]]:
    """Search symbols by name or ticker. exchange: us, nse, bse, or None for all."""
    settings = get_settings()
    if settings.fmp_api_key and (not exchange or exchange == "us"):
        data = _search_fmp(query, limit)
        if data:
            return [{"symbol": r["symbol"], "name": r.get("name") or r["symbol"], "exchange": "us"} for r in data]
    return _search_fallback(query, limit, exchange)


# US symbols and company name for search
_STOCK_UNIVERSE = [
    ("AAPL", "Apple", "us"), ("MSFT", "Microsoft", "us"), ("GOOGL", "Alphabet Google", "us"), ("AMZN", "Amazon", "us"),
    ("META", "Meta Facebook", "us"), ("NVDA", "NVIDIA", "us"), ("TSLA", "Tesla", "us"), ("BRK-B", "Berkshire Hathaway", "us"),
    ("JPM", "JPMorgan Chase", "us"), ("V", "Visa", "us"), ("JNJ", "Johnson & Johnson", "us"), ("WMT", "Walmart", "us"),
    ("PG", "Procter & Gamble", "us"), ("MA", "Mastercard", "us"), ("HD", "Home Depot", "us"), ("DIS", "Walt Disney", "us"),
    ("BAC", "Bank of America", "us"), ("ADBE", "Adobe", "us"), ("XOM", "Exxon Mobil", "us"), ("CVX", "Chevron", "us"),
    ("PFE", "Pfizer", "us"), ("NFLX", "Netflix", "us"), ("KO", "Coca-Cola", "us"), ("PEP", "PepsiCo", "us"), ("COST", "Costco", "us"),
    ("ABT", "Abbott", "us"), ("AVGO", "Broadcom", "us"), ("TMO", "Thermo Fisher", "us"), ("CSCO", "Cisco", "us"), ("ACN", "Accenture", "us"),
    ("DHR", "Danaher", "us"), ("NEE", "NextEra Energy", "us"), ("INTC", "Intel", "us"), ("AMD", "AMD", "us"), ("QCOM", "Qualcomm", "us"),
    ("TXN", "Texas Instruments", "us"), ("IBM", "IBM", "us"), ("ORCL", "Oracle", "us"), ("CRM", "Salesforce", "us"), ("NOW", "ServiceNow", "us"),
    ("INTU", "Intuit", "us"), ("AMAT", "Applied Materials", "us"), ("LMT", "Lockheed Martin", "us"), ("HON", "Honeywell", "us"),
    ("UNP", "Union Pacific", "us"), ("SPY", "SPDR S&P 500", "us"), ("QQQ", "Nasdaq 100 ETF", "us"), ("PYPL", "PayPal", "us"),
    ("UBER", "Uber", "us"), ("SHOP", "Shopify", "us"), ("SQ", "Block Square", "us"), ("ZM", "Zoom", "us"), ("SNOW", "Snowflake", "us"),
]
# NSE India symbols (Yahoo uses .NS suffix)
_NSE_UNIVERSE = [
    ("RELIANCE", "Reliance Industries", "nse"), ("TCS", "Tata Consultancy Services", "nse"), ("HDFCBANK", "HDFC Bank", "nse"),
    ("INFY", "Infosys", "nse"), ("ICICIBANK", "ICICI Bank", "nse"), ("HINDUNILVR", "Hindustan Unilever", "nse"),
    ("SBIN", "State Bank of India", "nse"), ("BHARTIARTL", "Bharti Airtel", "nse"), ("ITC", "ITC", "nse"),
    ("KOTAKBANK", "Kotak Mahindra Bank", "nse"), ("LT", "Larsen & Toubro", "nse"), ("AXISBANK", "Axis Bank", "nse"),
    ("ASIANPAINT", "Asian Paints", "nse"), ("MARUTI", "Maruti Suzuki", "nse"), ("TITAN", "Titan", "nse"),
    ("WIPRO", "Wipro", "nse"), ("SUNPHARMA", "Sun Pharma", "nse"), ("ULTRACEMCO", "UltraTech Cement", "nse"),
    ("BAJFINANCE", "Bajaj Finance", "nse"), ("NESTLEIND", "Nestle India", "nse"), ("HCLTECH", "HCL Tech", "nse"),
    ("TATAMOTORS", "Tata Motors", "nse"), ("INDUSINDBK", "IndusInd Bank", "nse"), ("POWERGRID", "Power Grid", "nse"),
    ("NIFTY 50", "Nifty 50 Index", "nse"), ("BANKNIFTY", "Bank Nifty", "nse"),
]
ALL_UNIVERSE = _STOCK_UNIVERSE + _NSE_UNIVERSE

def _search_fallback(query: str, limit: int, exchange_filter: Optional[str] = None) -> list[dict[str, Any]]:
    """Fallback search: match by ticker or company name. Search US + NSE unless exchange_filter set."""
    q = query.strip()
    universe = ALL_UNIVERSE
    if exchange_filter and exchange_filter.lower() in ("us", "nse", "bse"):
        ex = exchange_filter.lower()
        universe = [u for u in ALL_UNIVERSE if u[2] == ex]
    if not universe:
        universe = ALL_UNIVERSE
    if not q:
        return [{"symbol": u[0], "name": u[1], "exchange": u[2]} for u in universe[:limit]]
    q_lower = q.lower()
    q_upper = q.upper()
    matches = []
    for symbol, name, ex in universe:
        name_lower = (name or "").lower()
        if q_upper in symbol or q_lower in name_lower:
            matches.append({"symbol": symbol, "name": name, "exchange": ex})
        if len(matches) >= limit:
            break
    if not matches:
        try:
            for suf, ex in [("", "us"), (".NS", "nse"), (".BO", "bse")]:
                t = yf.Ticker(q_upper + suf)
                info = t.info
                sym = info.get("symbol") or ""
                if sym and (info.get("shortName") or info.get("longName")):
                    name = info.get("shortName") or info.get("longName") or q_upper
                    base = sym.replace(".NS", "").replace(".BO", "").upper()
                    matches = [{"symbol": base, "name": name, "exchange": ex}]
                    break
        except Exception:
            pass
    return matches[:limit]


def _search_fmp(query: str, limit: int) -> list[dict[str, Any]]:
    """Search symbols via Financial Modeling Prep API."""
    settings = get_settings()
    url = f"https://financialmodelingprep.com/api/v3/search?query={query}&limit={limit}&apikey={settings.fmp_api_key}"
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url)
            if r.status_code != 200:
                return _search_fallback(query, limit, None)
            data = r.json()
            return [{"symbol": item.get("symbol", ""), "name": item.get("name", "")} for item in (data or [])]
    except Exception:
        return _search_fallback(query, limit, None)


def get_multiple_quotes(symbols: list[str], exchange: str = "us") -> list[dict[str, Any]]:
    """Fetch quotes for multiple symbols (batch)."""
    result = []
    for s in symbols:
        s = (s or "").upper().strip()
        if not s:
            continue
        q = get_quote(s, exchange=exchange)
        if "error" not in q:
            result.append(q)
    return result
