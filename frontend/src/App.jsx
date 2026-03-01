import React, { useState, useCallback } from 'react'
import {
  searchSymbols,
  compareAll,
  getEarningsSummary,
  getAIScore,
  getAnalyze,
} from './api'
import './App.css'

function formatNum(n, decimals = 2) {
  if (n == null || n === '') return '—'
  const x = Number(n)
  if (Number.isNaN(x)) return '—'
  if (Math.abs(x) >= 1e9) return (x / 1e9).toFixed(decimals) + 'B'
  if (Math.abs(x) >= 1e6) return (x / 1e6).toFixed(decimals) + 'M'
  if (Math.abs(x) >= 1e3) return (x / 1e3).toFixed(decimals) + 'K'
  return x.toFixed(decimals)
}

function formatPct(n) {
  if (n == null || n === '') return '—'
  const x = Number(n)
  if (Number.isNaN(x)) return '—'
  const s = (x * 100).toFixed(2) + '%'
  return x >= 0 ? <span className="num-positive">{s}</span> : <span className="num-negative">{s}</span>
}

function formatPrice(n) {
  if (n == null || n === '') return '—'
  const x = Number(n)
  if (Number.isNaN(x)) return '—'
  return '$' + (x < 1 ? x.toFixed(4) : x.toFixed(2))
}

export default function App() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [watchlist, setWatchlist] = useState(['AAPL', 'MSFT', 'GOOGL'])
  const [compareData, setCompareData] = useState(null)
  const [loadingCompare, setLoadingCompare] = useState(false)
  const [compareError, setCompareError] = useState(null)
  const [detailSymbol, setDetailSymbol] = useState(null)
  const [detailData, setDetailData] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [exchange, setExchange] = useState('us')  // us | nse | bse | all (search only)

  const runSearch = useCallback(async () => {
    const q = searchQuery.trim()
    if (!q) return
    setSearching(true)
    setSearchResults([])
    try {
      const data = await searchSymbols(q, 15, exchange === 'all' ? null : exchange)
      setSearchResults(Array.isArray(data) ? data : [])
    } catch (e) {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }, [searchQuery, exchange])

  const addToWatchlist = (symbol, openDetails = false, symbolExchange = null) => {
    const s = (symbol || '').toUpperCase().trim()
    if (!s) return
    if (!watchlist.includes(s)) setWatchlist((prev) => [...prev, s])
    setSearchQuery('')
    setSearchResults([])
    if (openDetails) openDetail(s, symbolExchange || exchange)
  }

  const removeFromWatchlist = (symbol) => {
    setWatchlist((prev) => prev.filter((s) => s !== symbol))
  }

  const runCompare = useCallback(async () => {
    if (watchlist.length === 0) return
    setLoadingCompare(true)
    setCompareError(null)
    try {
      const data = await compareAll(watchlist, exchange === 'all' ? 'us' : exchange)
      setCompareData(data)
    } catch (e) {
      setCompareError(e.message)
      setCompareData(null)
    } finally {
      setLoadingCompare(false)
    }
  }, [watchlist, exchange])

  const openDetail = useCallback(async (symbol, symbolExchange = null) => {
    const ex = symbolExchange || exchange
    const effectiveExchange = ex === 'all' ? 'us' : ex
    setDetailSymbol(symbol)
    setDetailData(null)
    setLoadingDetail(true)
    try {
      const [summary, score, analyze] = await Promise.all([
        getEarningsSummary(symbol, null, null, effectiveExchange).catch(() => null),
        getAIScore(symbol, effectiveExchange).catch(() => null),
        getAnalyze(symbol, effectiveExchange).catch(() => null),
      ])
      setDetailData({ summary, score, analyze })
    } catch (e) {
      setDetailData({ error: e.message })
    } finally {
      setLoadingDetail(false)
    }
  }, [exchange])

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <h1>Market Intelligence Dashboard</h1>
          <p className="tagline">Fundamentals, earnings insights & AI-powered ranking</p>
        </div>
      </header>

      <main className="main">
        <section className="search-section card">
          <h2>Stock coverage & search</h2>
          <div className="search-row">
            <select
              className="exchange-select"
              value={exchange}
              onChange={(e) => setExchange(e.target.value)}
              title="Data source / exchange"
            >
              <option value="all">All (US + NSE)</option>
              <option value="us">US (Yahoo)</option>
              <option value="nse">NSE India</option>
              <option value="bse">BSE India</option>
            </select>
            <input
              type="text"
              placeholder="Search by symbol or name (e.g. AAPL, Apple, RELIANCE, TCS)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runSearch()}
            />
            <button type="button" onClick={runSearch} disabled={searching}>
              {searching ? 'Searching…' : 'Search'}
            </button>
          </div>
          {searchResults.length > 0 && (
            <>
              <p className="search-hint">Click any stock to load full details including <strong>AI analysis, prediction & hints</strong>. Or use &quot;Add & load all&quot; to add to watchlist and open details.</p>
              <ul className="search-results">
              {searchResults.map((r) => (
                <li
                  key={`${r.symbol}-${r.exchange || 'us'}`}
                  className="search-result-row"
                  onClick={() => openDetail(r.symbol, r.exchange)}
                >
                  <span className="sym">{r.symbol}</span>
                  <span className="name">{r.name}</span>
                  <span className="exchange-badge">{((r.exchange || 'us').toUpperCase())}</span>
                  <span className="ai-badge">AI</span>
                  <button
                    type="button"
                    className="add-btn"
                    onClick={(e) => { e.stopPropagation(); addToWatchlist(r.symbol, true, r.exchange); }}
                  >
                    Add & load all
                  </button>
                </li>
              ))}
            </ul>
            </>
          )}
          {!searching && searchQuery.trim() && searchResults.length === 0 && (
            <p className="search-empty">No symbols found for &quot;{searchQuery.trim()}&quot;. Try ticker (e.g. AAPL) or company name (e.g. Apple, Microsoft).</p>
          )}
          <div className="watchlist">
            <span className="label">Watchlist:</span>
            {watchlist.map((s) => (
              <span key={s} className="chip chip-clickable">
                <span onClick={() => openDetail(s, exchange === 'all' ? 'us' : exchange)}>{s}</span>
                <button type="button" aria-label={`Remove ${s}`} onClick={(e) => { e.stopPropagation(); removeFromWatchlist(s); }}>×</button>
              </span>
            ))}
            {watchlist.length === 0 && <span className="muted">Add symbols via search</span>}
          </div>
          <div className="actions">
            <button
              type="button"
              className="primary-btn"
              onClick={runCompare}
              disabled={watchlist.length === 0 || loadingCompare}
            >
              {loadingCompare ? 'Comparing…' : 'Compare all & rank'}
            </button>
          </div>
          {compareError && <p className="error">{compareError}</p>}
        </section>

        {compareData && compareData.symbols && compareData.symbols.length > 0 && (
          <section className="compare-section card">
            <h2>Compare & ranking (AI + ML)</h2>
            <div className="table-wrap">
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Symbol</th>
                    <th>Price</th>
                    <th>Change %</th>
                    <th>P/E</th>
                    <th>Market cap</th>
                    <th>Rev growth</th>
                    <th>AI score</th>
                    <th>ML score</th>
                    <th>Combined</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {compareData.symbols.map((row) => (
                    <tr key={row.symbol} onClick={() => openDetail(row.symbol)}>
                      <td><strong>#{row.rank}</strong></td>
                      <td><strong>{row.symbol}</strong></td>
                      <td>{formatPrice(row.quote?.price)}</td>
                      <td>{formatPct(row.quote?.change_percent != null ? row.quote.change_percent / 100 : null)}</td>
                      <td>{row.quote?.pe_ratio != null ? Number(row.quote.pe_ratio).toFixed(1) : '—'}</td>
                      <td>{formatNum(row.quote?.market_cap)}</td>
                      <td>{formatPct(row.fundamentals?.revenue_growth)}</td>
                      <td>{row.ai_score != null ? row.ai_score : '—'}</td>
                      <td>{row.ml_score != null ? row.ml_score : '—'}</td>
                      <td><strong>{row.combined_score != null ? row.combined_score : '—'}</strong></td>
                      <td><button type="button" className="detail-link">Details</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {detailSymbol && (
          <section className="detail-section card">
            <div className="detail-header">
              <h2>{detailSymbol} – AI analysis, prediction & hints</h2>
              <button type="button" className="close-btn" onClick={() => { setDetailSymbol(null); setDetailData(null); }}>×</button>
            </div>
            {loadingDetail && <p>Loading…</p>}
            {detailData && !loadingDetail && (
              <div className="detail-content">
                {detailData.error && <p className="error">{detailData.error}</p>}
                {detailData.analyze && (
                  <div className="detail-block ai-insight-block">
                    <h3>AI analysis (like a human analyst)</h3>
                    {detailData.analyze.analysis && <p className="analysis-text">{detailData.analyze.analysis}</p>}
                    {detailData.analyze.prediction_outlook && (
                      <p className="outlook-text"><strong>Prediction & outlook:</strong> {detailData.analyze.prediction_outlook}</p>
                    )}
                    {detailData.analyze.hints && detailData.analyze.hints.length > 0 && (
                      <div className="hints-box">
                        <strong>Actionable hints:</strong>
                        <ul className="hints-list">
                          {detailData.analyze.hints.map((h, i) => <li key={i}>{h}</li>)}
                        </ul>
                      </div>
                    )}
                    {detailData.analyze.error && <p className="muted">{detailData.analyze.error}</p>}
                    <div className="trend-box">
                      <h4>Data-driven trend</h4>
                      {detailData.analyze.trend && (
                        <p>
                          {detailData.analyze.trend.trend_5d_pct != null && `5-day: ${detailData.analyze.trend.trend_5d_pct}%`}
                          {detailData.analyze.trend.trend_20d_pct != null && ` · 20-day: ${detailData.analyze.trend.trend_20d_pct}%`}
                          {detailData.analyze.trend.trend_direction && ` · Direction: ${detailData.analyze.trend.trend_direction}`}
                        </p>
                      )}
                      {detailData.analyze.prediction_note && <p className="prediction-note">{detailData.analyze.prediction_note}</p>}
                      {detailData.analyze.support_resistance && <p className="muted small">{detailData.analyze.support_resistance}</p>}
                    </div>
                  </div>
                )}
                {detailData.score && (
                  <div className="detail-block">
                    <h3>AI & ML score</h3>
                    <p><strong>AI score:</strong> {detailData.score.ai_score ?? '—'} &nbsp; <strong>ML score:</strong> {detailData.score.ml_score ?? '—'}</p>
                    {detailData.score.rationale && <p className="rationale">{detailData.score.rationale}</p>}
                  </div>
                )}
                {detailData.summary && (
                  <div className="detail-block">
                    <h3>Earnings call summary (AI)</h3>
                    {detailData.summary.available && detailData.summary.ai_summary ? (
                      <>
                        <p className="summary-text">{detailData.summary.ai_summary}</p>
                        {detailData.summary.sentiment && <p><strong>Sentiment:</strong> {detailData.summary.sentiment}</p>}
                        {detailData.summary.highlights?.length > 0 && (
                          <ul>
                            {detailData.summary.highlights.map((h, i) => <li key={i}>{h}</li>)}
                          </ul>
                        )}
                      </>
                    ) : (
                      <p className="muted">{detailData.summary.message || 'No transcript or summary available. Set FMP_API_KEY and OPENAI_API_KEY for earnings AI.'}</p>
                    )}
                  </div>
                )}
                {detailData.score?.fundamentals && (
                  <div className="detail-block">
                    <h3>Key fundamentals</h3>
                    <div className="fund-grid">
                      <span>Revenue growth: {formatPct(detailData.score.fundamentals.revenue_growth)}</span>
                      <span>Earnings growth: {formatPct(detailData.score.fundamentals.earnings_growth)}</span>
                      <span>Profit margin: {formatPct(detailData.score.fundamentals.profit_margin)}</span>
                      <span>ROE: {formatPct(detailData.score.fundamentals.return_on_equity)}</span>
                      <span>Free cash flow: {formatNum(detailData.score.fundamentals.free_cash_flow)}</span>
                      <span>Debt/Equity: {detailData.score.fundamentals.debt_to_equity != null ? Number(detailData.score.fundamentals.debt_to_equity).toFixed(2) : '—'}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </main>

      <footer className="footer">
        <p>Data: Yahoo Finance (quotes & fundamentals). Earnings transcripts: FMP API. AI: OpenAI. Refresh and compare to update.</p>
      </footer>
    </div>
  )
}
