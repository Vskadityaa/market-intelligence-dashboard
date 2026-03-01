"""LLM service: earnings summarization and AI Score (ranking)."""
from __future__ import annotations

import os
from typing import Any, Optional

from config import get_settings


def summarize_earnings_transcript(transcript_text: str, symbol: str, max_tokens: int = 800) -> dict[str, Any]:
    """
    Use LLM to synthesize earnings call transcript into actionable intelligence.
    Returns summary, key metrics mentioned, and sentiment/bullets.
    """
    settings = get_settings()
    if not settings.openai_api_key or not transcript_text or len(transcript_text.strip()) < 100:
        return {
            "symbol": symbol,
            "summary": None,
            "key_metrics": [],
            "highlights": [],
            "sentiment": None,
            "error": "OpenAI API key not set or transcript too short." if not settings.openai_api_key else "Transcript too short to summarize.",
        }

    system = (
        "You are a financial analyst. Summarize earnings call transcripts into actionable intelligence. "
        "Output: 1) A concise executive summary (2-3 paragraphs). "
        "2) Key metrics mentioned (revenue, EPS, guidance, margins, etc.). "
        "3) 3-5 bullet highlights. "
        "4) Sentiment: Bullish / Neutral / Cautious. Be factual and concise."
    )
    user = f"Symbol: {symbol}\n\nTranscript (excerpt):\n{transcript_text[:12000]}"

    response = _chat_completion(system=system, user=user, max_tokens=max_tokens)
    if "error" in response:
        return {"symbol": symbol, "summary": None, "key_metrics": [], "highlights": [], "sentiment": None, "error": response["error"]}

    text = response.get("content", "")
    # Parse structured parts from model output (model can return markdown sections)
    summary = text
    key_metrics = []
    highlights = []
    sentiment = None
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("**Key metrics") or "Key metrics" in line:
            continue
        if line.startswith("- ") or line.startswith("* "):
            highlights.append(line.lstrip("-* ").strip())
        if "Bullish" in line or "Neutral" in line or "Cautious" in line:
            for s in ("Bullish", "Neutral", "Cautious"):
                if s in line:
                    sentiment = s
                    break

    return {
        "symbol": symbol,
        "summary": summary,
        "key_metrics": key_metrics or ["See summary for metrics."],
        "highlights": highlights[:5] if highlights else ["See summary above."],
        "sentiment": sentiment or "Neutral",
        "error": None,
    }


def compute_ai_score(
    symbol: str,
    fundamentals: dict[str, Any],
    quote: dict[str, Any],
    summary_sentiment: Optional[str] = None,
    max_tokens: int = 400,
) -> dict[str, Any]:
    """
    Use LLM to produce an AI Score (0-100) and short rationale for ranking companies.
    Incorporates fundamentals, valuation, and optional earnings sentiment.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return {
            "symbol": symbol,
            "ai_score": None,
            "rationale": "Set OPENAI_API_KEY in .env to enable AI Score.",
            "rank": None,
        }

    # Build context for LLM
    fund = fundamentals or {}
    q = quote or {}
    context = [
        f"Symbol: {symbol}",
        f"Price: {q.get('price')} | P/E: {q.get('pe_ratio')} | Forward P/E: {q.get('forward_pe')}",
        f"Market cap: {q.get('market_cap')} | Sector: {q.get('sector')}",
        f"Revenue growth: {fund.get('revenue_growth')} | Earnings growth: {fund.get('earnings_growth')}",
        f"Profit margin: {fund.get('profit_margin')} | ROE: {fund.get('return_on_equity')}",
        f"Debt/Equity: {fund.get('debt_to_equity')} | Free cash flow: {fund.get('free_cash_flow')}",
        f"Earnings sentiment (from transcript): {summary_sentiment or 'N/A'}",
    ]
    user = "\n".join(context)

    system = (
        "You are a quantitative analyst. Given fundamental and valuation data, output:\n"
        "1) AI Score: a number from 0 to 100 (integer), considering growth, profitability, valuation, and optional sentiment.\n"
        "2) Rationale: 2-3 short sentences explaining the score.\n"
        "Format your reply as: AI Score: <number> then Rationale: <text>"
    )

    response = _chat_completion(system=system, user=user, max_tokens=max_tokens)
    if "error" in response:
        return {"symbol": symbol, "ai_score": None, "rationale": response["error"], "rank": None}

    text = response.get("content", "")
    ai_score = None
    rationale = text
    for word in text.replace(":", " ").split():
        if word.isdigit():
            num = int(word)
            if 0 <= num <= 100:
                ai_score = num
                break
    if "Rationale:" in text:
        rationale = text.split("Rationale:")[-1].strip()

    return {
        "symbol": symbol,
        "ai_score": ai_score,
        "rationale": rationale[:500],
        "rank": None,  # Rank filled by caller when comparing multiple
    }


def get_ai_analysis_and_hints(
    symbol: str,
    quote: dict[str, Any],
    fundamentals: dict[str, Any],
    trend_info: dict[str, Any],
    earnings_sentiment: Optional[str] = None,
    max_tokens: int = 1000,
) -> dict[str, Any]:
    """
    AI analyzes the stock and responds like a human analyst: plain-English summary,
    value prediction outlook, and 3–5 actionable hints. No jargon overload.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return {
            "symbol": symbol,
            "analysis": None,
            "hints": [],
            "prediction_outlook": None,
            "error": "Set OPENAI_API_KEY in .env to get AI analysis and hints.",
        }

    q = quote or {}
    f = fundamentals or {}
    t = trend_info or {}
    name = q.get("name") or symbol
    price = q.get("price")
    pe = q.get("pe_ratio")
    sector = q.get("sector")
    rev_growth = f.get("revenue_growth")
    earn_growth = f.get("earnings_growth")
    profit_margin = f.get("profit_margin")
    roe = f.get("return_on_equity")
    debt_equity = f.get("debt_to_equity")
    trend_5d = t.get("trend_5d_pct")
    trend_20d = t.get("trend_20d_pct")
    trend_dir = t.get("trend_direction")
    prediction_note = t.get("prediction_note")

    context_parts = [
        f"Stock: {name} ({symbol}). Price: ${price}. P/E: {pe}. Sector: {sector}.",
        f"Fundamentals: Revenue growth {rev_growth}, Earnings growth {earn_growth}, Profit margin {profit_margin}, ROE {roe}, Debt/Equity {debt_equity}.",
        f"Recent trend: 5-day return {trend_5d}%, 20-day {trend_20d}%. Direction: {trend_dir}. Data note: {prediction_note}.",
    ]
    if earnings_sentiment:
        context_parts.append(f"Earnings call sentiment: {earnings_sentiment}.")
    user_context = "\n".join(context_parts)

    system = (
        "You are a friendly, experienced stock analyst talking to a normal investor. "
        "Write like a human: clear, honest, and helpful. Do NOT use heavy jargon. "
        "Your reply MUST have exactly these three sections, each starting on a new line with the exact label:\n\n"
        "**Analysis:**\n(2–4 sentences: what this stock is, how the business looks, and how valuation/trend fits. Plain English.)\n\n"
        "**Prediction & Outlook:**\n(2–3 sentences: short-term and medium-term outlook, and what could go right or wrong. Sound like a human giving a view, not a robot.)\n\n"
        "**Hints:**\n(3–5 short, actionable hints. Each on a new line starting with a dash. Examples: 'Watch the next earnings date.', 'Consider adding on dips below $X.', 'Compare P/E with sector average.' Be specific and practical.)"
    )

    response = _chat_completion(system=system, user=user_context, max_tokens=max_tokens)
    if "error" in response:
        return {
            "symbol": symbol,
            "analysis": None,
            "hints": [],
            "prediction_outlook": None,
            "error": response["error"],
        }

    text = response.get("content", "")
    analysis = None
    prediction_outlook = None
    hints = []
    current_section = None
    for line in text.split("\n"):
        line_stripped = line.strip()
        if line_stripped.startswith("**Analysis:**"):
            current_section = "analysis"
            rest = line_stripped.replace("**Analysis:**", "").strip()
            if rest:
                analysis = rest
            continue
        if line_stripped.startswith("**Prediction & Outlook:**") or line_stripped.startswith("**Prediction and Outlook:**"):
            current_section = "outlook"
            rest = line_stripped.split(":**", 1)[-1].strip() if ":**" in line_stripped else ""
            if rest:
                prediction_outlook = rest
            continue
        if "**Hints:**" in line_stripped:
            current_section = "hints"
            rest = line_stripped.split("**Hints:**", 1)[-1].strip().lstrip("-* ").strip()
            if rest:
                hints.append(rest)
            continue
        if current_section == "analysis" and line_stripped:
            analysis = (analysis or "") + " " + line_stripped
        elif current_section == "outlook" and line_stripped:
            prediction_outlook = (prediction_outlook or "") + " " + line_stripped
        elif current_section == "hints" and (line_stripped.startswith("-") or line_stripped.startswith("*")):
            hints.append(line_stripped.lstrip("-* ").strip())

    if not analysis and text:
        analysis = text[:600]
    hints = [h for h in hints if h][:5]

    return {
        "symbol": symbol,
        "analysis": (analysis or "").strip() or None,
        "hints": hints,
        "prediction_outlook": (prediction_outlook or "").strip() or None,
        "error": None,
    }


def _chat_completion(system: str, user: str, max_tokens: int = 600) -> dict[str, Any]:
    """Call OpenAI-compatible chat API."""
    settings = get_settings()
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url or None)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content if resp.choices else ""
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}
