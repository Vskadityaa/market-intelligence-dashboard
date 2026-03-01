# Market Intelligence Dashboard

A **searchable dashboard** that consolidates **fundamental financial metrics**, **earnings call insights**, and **AI/ML-powered ranking** into one interface.

## Features

- **Stock coverage & search** – Search by symbol or name; maintain a watchlist and analyze across your sample set.
- **AI-powered earnings synthesis** – Earnings call transcripts (when available) are summarized into actionable bullets, key metrics, and sentiment via an LLM.
- **Fundamental data** – Automated integration of key metrics: revenue, earnings growth, margins, ROE, debt, free cash flow, P/E, market cap, etc.
- **AI Score + ML score** – Companies are ranked using:
  - **LLM (AI) score**: 0–100 from fundamentals + valuation + optional transcript sentiment.
  - **ML score**: 0–100 from a weighted combination of normalized fundamental features (growth, profitability, leverage, valuation).
  - **Combined score** used for ranking when comparing multiple symbols.
- **Compare all** – Select symbols, run “Compare all & rank” to get a table with quotes, fundamentals, AI/ML scores, and rank.
- **Regular updates** – Re-run compare and refresh the page to get updated data; backend can be extended with scheduled jobs for automatic refresh.

## Tech stack

- **Backend**: Python, FastAPI, yfinance (quotes & fundamentals), optional FMP API (earnings transcripts), OpenAI-compatible LLM (summarization + AI Score), scikit-learn (ML score).
- **Frontend**: React, Vite; proxy to backend for API calls.

## Quick start

### 1. Backend (Python)

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Copy env example and add keys (optional but recommended for full features):

```bash
copy .env.example .env
```

Edit `.env`:

- **OPENAI_API_KEY** – Required for earnings summarization and AI Score. Use OpenAI or any OpenAI-compatible endpoint (e.g. Azure, local).
- **FMP_API_KEY** – Optional; required for earnings call **transcripts**. Get a free key at [Financial Modeling Prep](https://site.financialmodelingprep.com/developer/docs).
- **ALPHA_VANTAGE_API_KEY** – Optional; not used by default (yfinance provides quotes/fundamentals).

Run the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python main.py
```

API docs: **http://127.0.0.1:8000/docs**

### 2. Frontend (Node)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. The Vite dev server proxies `/api` to the backend.

### 3. Production build

```bash
cd frontend
npm run build
```

Serve the `frontend/dist` folder with any static server and ensure it can reach the backend at the same origin or configure CORS and `BASE` in `frontend/src/api.js`.

## API overview

| Endpoint | Description |
|----------|-------------|
| `GET /api/search?q=...` | Search symbols (ticker/name). |
| `GET /api/quote/{symbol}` | Current quote and key metrics. |
| `GET /api/fundamentals/{symbol}` | Fundamental financial data. |
| `GET /api/quote/batch?symbols=AAPL,MSFT` | Batch quotes. |
| `GET /api/earnings/transcript/{symbol}` | Raw earnings transcript (FMP). |
| `GET /api/earnings/summary/{symbol}` | Transcript + AI summary (FMP + OpenAI). |
| `GET /api/score/{symbol}` | AI Score, ML score, rationale. |
| `POST /api/compare` | Body: `{ "symbols": ["AAPL","MSFT",...] }` – returns ranked comparison. |

## Data sources

- **Quotes & fundamentals**: Yahoo Finance via **yfinance** (no API key).
- **Earnings transcripts**: **Financial Modeling Prep** (set `FMP_API_KEY`).
- **AI summarization & AI Score**: **OpenAI** or compatible API (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`).

## Post-deployment: continuous optimization

- **Refresh**: Use “Compare all & rank” and reload the dashboard to pull fresh data.
- **Scheduled refresh**: In `backend/main.py`, enable the APScheduler in the lifespan and implement a `refresh_cache()` job (e.g. re-fetch top symbols every 6 hours) to keep data current.
- **Tuning**: Adjust ML weights in `backend/services/ml_scorer.py` and LLM prompts in `backend/services/llm_service.py` to align scores with your criteria.

## License

Use for personal or internal use. Comply with Yahoo Finance, FMP, and OpenAI terms of service where applicable.
