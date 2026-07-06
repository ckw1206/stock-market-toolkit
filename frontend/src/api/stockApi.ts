import axios from "axios";
import type { StockData, Indicators, StockInfo, Fundamentals, DividendData, NewsData } from "../types";

const API = import.meta.env.VITE_API_URL || "";

function getToken(): string | null {
  return localStorage.getItem("access_token");
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getStock(symbol: string, period: string): Promise<StockData> {
  const res = await axios.get(`${API}/api/stock/${symbol}`, {
    params: { period },
    headers: authHeaders(),
  });
  return res.data;
}

export async function getIndicators(symbol: string, period: string): Promise<Indicators> {
  const res = await axios.get(`${API}/api/stock/${symbol}/indicators`, {
    params: { period },
    headers: authHeaders(),
  });
  return res.data;
}

export async function getStockInfo(symbol: string): Promise<StockInfo> {
  const res = await axios.get(`${API}/api/stock/${symbol}/info`, {
    headers: authHeaders(),
  });
  return res.data;
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
