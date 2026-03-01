const BASE = '';

async function checkResponse(res) {
  if (res.ok) return res;
  let msg = res.statusText;
  try {
    const body = await res.json();
    if (body && typeof body.detail === 'string') msg = body.detail;
    else if (body && typeof body.detail === 'object' && body.detail.message) msg = body.detail.message;
  } catch (_) {}
  throw new Error(msg);
}

export async function searchSymbols(q, limit = 20, exchange = null) {
  let url = `${BASE}/api/search?q=${encodeURIComponent(q)}&limit=${limit}`;
  if (exchange && exchange !== 'all') url += `&exchange=${encodeURIComponent(exchange)}`;
  const res = await fetch(url);
  await checkResponse(res);
  return res.json();
}

export async function getQuote(symbol, exchange = 'us') {
  const res = await fetch(`${BASE}/api/quote/${encodeURIComponent(symbol)}?exchange=${encodeURIComponent(exchange)}`);
  await checkResponse(res);
  return res.json();
}

export async function getFundamentals(symbol, exchange = 'us') {
  const res = await fetch(`${BASE}/api/fundamentals/${encodeURIComponent(symbol)}?exchange=${encodeURIComponent(exchange)}`);
  await checkResponse(res);
  return res.json();
}

export async function compareAll(symbols, exchange = 'us') {
  const res = await fetch(`${BASE}/api/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbols, exchange: exchange || 'us' }),
  });
  await checkResponse(res);
  return res.json();
}

export async function getEarningsSummary(symbol, year, quarter, exchange = 'us') {
  let url = `${BASE}/api/earnings/summary/${encodeURIComponent(symbol)}?exchange=${encodeURIComponent(exchange)}`;
  if (year != null) url += `&year=${year}`;
  if (quarter != null) url += `&quarter=${quarter}`;
  const res = await fetch(url);
  await checkResponse(res);
  return res.json();
}

export async function getAIScore(symbol, exchange = 'us') {
  const res = await fetch(`${BASE}/api/score/${encodeURIComponent(symbol)}?exchange=${encodeURIComponent(exchange)}`);
  await checkResponse(res);
  return res.json();
}

export async function getAnalyze(symbol, exchange = 'us') {
  const res = await fetch(`${BASE}/api/analyze/${encodeURIComponent(symbol)}?exchange=${encodeURIComponent(exchange)}`);
  await checkResponse(res);
  return res.json();
}
