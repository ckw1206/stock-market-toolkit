import axios from "axios";
import type { StockData, Indicators, StockInfo, Fundamentals, DividendData, NewsData } from "../types";

export const API = import.meta.env.VITE_API_URL || "";

export function getToken(): string | null {
  return localStorage.getItem("access_token");
}

export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Ticker data cache ──
// In-memory TTL cache with in-flight dedup so per-symbol data fetched once
// (e.g. preloaded at login) is reused across pages instead of re-fetched on
// every navigation. Mirrors the backend's services/cache.py contract.
const _cache = new Map<string, { at: number; value: unknown }>();
const _inflight = new Map<string, Promise<unknown>>();

const PRICE_TTL_MS = 60_000; // OHLCV + indicators move intraday
const INFO_TTL_MS = 3_600_000; // company info is near-static

async function cachedGet<T>(key: string, ttlMs: number, loader: () => Promise<T>): Promise<T> {
  const hit = _cache.get(key);
  if (hit && Date.now() - hit.at < ttlMs) return hit.value as T;
  const pending = _inflight.get(key);
  if (pending) return pending as Promise<T>;
  const p = loader()
    .then((value) => {
      _cache.set(key, { at: Date.now(), value });
      return value;
    })
    .finally(() => _inflight.delete(key));
  _inflight.set(key, p);
  return p;
}

/** Drop all cached ticker data (call on logout — cache may be user-scoped). */
export function clearTickerCache(): void {
  _cache.clear();
}

/** Warm the cache for the user's watchlist so pages open with data already
 * loaded. Sequential on purpose: a login should not fan out dozens of
 * concurrent requests. Best-effort — failures are ignored. */
export async function preloadTickers(period: string = "1mo"): Promise<void> {
  try {
    const { getWatchlist } = await import("./watchlistApi");
    const items = await getWatchlist();
    for (const item of items) {
      const symbol = item.symbol.toUpperCase();
      try {
        await Promise.all([getStock(symbol, period), getIndicators(symbol, period)]);
      } catch {
        // preload is best-effort; pages fetch on demand anyway
      }
    }
  } catch {
    // no watchlist / not authenticated — nothing to preload
  }
}

export async function getStock(symbol: string, period: string): Promise<StockData> {
  return cachedGet(`stock:${symbol.toUpperCase()}:${period}`, PRICE_TTL_MS, async () => {
    const res = await axios.get(`${API}/api/stock/${symbol}`, {
      params: { period },
      headers: authHeaders(),
    });
    return res.data;
  });
}

export async function getIndicators(symbol: string, period: string): Promise<Indicators> {
  return cachedGet(`indicators:${symbol.toUpperCase()}:${period}`, PRICE_TTL_MS, async () => {
    const res = await axios.get(`${API}/api/stock/${symbol}/indicators`, {
      params: { period },
      headers: authHeaders(),
    });
    return res.data;
  });
}

export async function getStockInfo(symbol: string): Promise<StockInfo> {
  return cachedGet(`info:${symbol.toUpperCase()}`, INFO_TTL_MS, async () => {
    const res = await axios.get(`${API}/api/stock/${symbol}/info`, {
      headers: authHeaders(),
    });
    return res.data;
  });
}

export async function getFundamentals(symbol: string): Promise<Fundamentals> {
  const res = await axios.get(`${API}/api/stock/${symbol}/fundamentals`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function getDividends(symbol: string): Promise<DividendData> {
  const res = await axios.get(`${API}/api/stock/${symbol}/dividends`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function getNews(symbol: string): Promise<NewsData> {
  const res = await axios.get(`${API}/api/stock/${symbol}/news`, {
    headers: authHeaders(),
  });
  return res.data;
}

export interface SymbolSuggestion {
  symbol: string;
  name: string;
  exchange: string;
}

export async function compareStocks(symbols: string[], period: string): Promise<{ stocks: StockData[] }> {
  const res = await axios.post(
    `${API}/api/compare`,
    { symbols, period },
    { headers: authHeaders() }
  );
  return res.data;
}

export async function searchSymbols(q: string): Promise<SymbolSuggestion[]> {
  const res = await axios.get(`${API}/api/search`, {
    params: { q },
  });
  const data = res.data;
  return Array.isArray(data) ? data : (data.suggestions || []);
}

export interface TopSignalItem {
  symbol: string;
  signal: string;
  confidence: number;
  price: number;
  rvol: number | null;
  breakout: boolean;
  volume_spike: boolean;
  reasons: string[];
  rank: number;
}

export interface TopSignalsData {
  scanned_at: string | null;
  buys: TopSignalItem[];
  sells: TopSignalItem[];
}

export async function getTopSignals(limit: number = 10): Promise<TopSignalsData> {
  const res = await axios.get(`${API}/api/signals/top`, {
    params: { limit },
    headers: authHeaders(),
  });
  return res.data;
}

export interface ScreenerItem {
  symbol: string;
  signal: string;
  score: number;
  confidence: number;
  price: number | null;
  rvol: number | null;
  breakout: boolean;
  volume_spike: boolean;
  rsi: number | null;
  sma20: number | null;
  sma50: number | null;
  volume_ratio: number | null;
  pct_from_52w_high: number | null;
  pct_change_1d: number | null;
  gap_and_go: boolean;
  sector: string | null;
  rank: number | null;
}

export interface ScreenerData {
  scanned_at: string | null;
  count: number;
  results: ScreenerItem[];
}

export interface ScreenerFilters {
  signal?: string;
  rsi_min?: number;
  rsi_max?: number;
  rvol_min?: number;
  breakout?: boolean;
  price_min?: number;
  price_max?: number;
  pct_from_52w_high_min?: number;
  above_sma50?: boolean;
  sector?: string;
  gap_min?: number;
  gap_max?: number;
  gap_and_go?: boolean;
  sort?: string;
  order?: "asc" | "desc";
  limit?: number;
}

export async function getScreener(filters: ScreenerFilters): Promise<ScreenerData> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== "")
  );
  const res = await axios.get(`${API}/api/screener`, {
    params,
    headers: authHeaders(),
  });
  return res.data;
}

export interface HeatmapSymbol {
  symbol: string;
  pct_change_1d: number | null;
  price: number | null;
  signal: string;
  rvol: number | null;
}

export interface HeatmapSector {
  sector: string;
  symbols: HeatmapSymbol[];
}

export interface HeatmapData {
  scanned_at: string | null;
  sectors: HeatmapSector[];
}

export async function getHeatmap(): Promise<HeatmapData> {
  const res = await axios.get(`${API}/api/heatmap`, {
    headers: authHeaders(),
  });
  return res.data;
}

export interface BreadthHistoryPoint {
  date: string | null;
  pct_above_sma50: number | null;
}

export interface MarketBreadthData {
  scanned_at: string | null;
  total_symbols: number;
  pct_above_sma50: number | null;
  advancers: number;
  decliners: number;
  new_highs: number;
  regime: "risk_on" | "neutral" | "risk_off";
  history: BreadthHistoryPoint[];
}

export async function getMarketBreadth(): Promise<MarketBreadthData> {
  const res = await axios.get(`${API}/api/market/breadth`, {
    headers: authHeaders(),
  });
  return res.data;
}

export interface PaperPosition {
  symbol: string;
  qty: number;
  avg_cost: number;
  last_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
}

export interface PaperPortfolioData {
  cash: number;
  starting_cash: number;
  positions: PaperPosition[];
  equity: number;
  total_unrealized_pnl: number;
}

export interface PaperTradeRecord {
  id: number;
  symbol: string;
  side: "buy" | "sell";
  qty: number;
  price: number;
  executed_at: string | null;
}

export async function getPaperPortfolio(): Promise<PaperPortfolioData> {
  const res = await axios.get(`${API}/api/paper/portfolio`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function getPaperHistory(): Promise<{ trades: PaperTradeRecord[] }> {
  const res = await axios.get(`${API}/api/paper/history`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function postPaperTrade(
  symbol: string,
  side: "buy" | "sell",
  qty: number,
  executedAt?: string | null
): Promise<{ symbol: string; side: string; qty: number; price: number; cash_after: number }> {
  const res = await axios.post(
    `${API}/api/paper/trade`,
    { symbol, side, qty, ...(executedAt ? { executed_at: executedAt } : {}) },
    { headers: authHeaders() }
  );
  return res.data;
}

export async function deletePaperTrade(tradeId: number): Promise<void> {
  await axios.delete(`${API}/api/paper/trade/${tradeId}`, { headers: authHeaders() });
}

export async function resetPaperPortfolio(
  startingCash?: number
): Promise<PaperPortfolioData> {
  const res = await axios.post(
    `${API}/api/paper/reset`,
    startingCash != null ? { starting_cash: startingCash } : {},
    { headers: authHeaders() }
  );
  return res.data;
}

export interface PositionSizePlan {
  symbol: string;
  account: number;
  risk_pct: number;
  atr_mult: number;
  entry: number;
  atr: number | null;
  stop: number | null;
  shares: number;
  risk_amount: number;
  take_profit_2r: number | null;
  take_profit_3r: number | null;
}

export async function getPositionSize(
  symbol: string,
  account: number,
  riskPct: number,
  atrMult: number = 2.0
): Promise<PositionSizePlan> {
  const res = await axios.get(`${API}/api/analysis/${symbol}/position-size`, {
    params: { account, risk_pct: riskPct, atr_mult: atrMult },
    headers: authHeaders(),
  });
  return res.data;
}
