export interface StockData {
  symbol: string;
  period: string;
  cached_at: string;
  timestamp: string[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  volume: number[];
}

export interface Indicators extends StockData {
  sma20: (number | null)[];
  sma50: (number | null)[];
  sma200: (number | null)[];
  ema12: (number | null)[];
  ema26: (number | null)[];
  rsi: (number | null)[];
  macd: (number | null)[];
  macd_signal: (number | null)[];
  macd_hist: (number | null)[];
  bb_upper: (number | null)[];
  bb_middle: (number | null)[];
  bb_lower: (number | null)[];
  atr: (number | null)[];
}

export interface StockInfo {
  symbol: string;
  cached_at: string;
  short_name: string;
  long_name?: string;
  exchange?: string;
  sector?: string;
  industry?: string;
  price: number;
  currency?: string;
  market_cap: number | null;
  trailing_pe: number | null;
  forward_pe: number | null;
  dividend_yield: number | null;
  beta: number | null;
  week_52_high: number | null;
  week_52_low: number | null;
  avg_volume: number | null;
}

export const TIMEFRAMES = [
  { label: "1D", value: "1d" },
  { label: "5D", value: "5d" },
  { label: "1M", value: "1mo" },
  { label: "3M", value: "3mo" },
  { label: "6M", value: "6mo" },
  { label: "1Y", value: "1y" },
  { label: "2Y", value: "2y" },
  { label: "5Y", value: "5y" },
  { label: "Max", value: "max" },
];

export interface ProfitabilityMetrics {
  roe: number | null;
  roa: number | null;
  gross_margin: number | null;
  op_margin: number | null;
  net_margin: number | null;
  eps_growth: number | null;
  rev_growth: number | null;
}

export interface DividendQualityDetails {
  score: number;
  has_dividends: boolean;
  consistent: boolean;
  growth: number | null;
  payout_ratio: number | null;
}

export interface Fundamentals {
  symbol: string;
  cached_at: string;
  f_score: number;
  profitability: ProfitabilityMetrics;
  dividend_quality: DividendQualityDetails;
  statements?: Record<string, unknown>;
}

export interface YearlyDividend {
  year: number;
  total: number;
}

export interface DividendData {
  symbol: string;
  cached_at: string;
  yearly: YearlyDividend[];
  yield_pct: number | null;
  payout_ratio: number | null;
  streak: number;
}

export interface NewsArticle {
  title: string;
  publisher?: string;
  link: string;
  publishedAt?: number;  // unix epoch
}

export interface NewsData {
  symbol: string;
  cached_at: string;
  articles: NewsArticle[];
}

export type SignalDirection = "bullish" | "bearish" | "neutral";

export type SignalType = 
  | "rsi_oversold" 
  | "rsi_overbought" 
  | "macd_cross" 
  | "sma_cross" 
  | "bb_touch" 
  | "volume_spike";

export interface Signal {
  id: string;
  symbol: string;
  direction: SignalDirection;
  signal_type: SignalType;
  price: number;
  timestamp: string;
  strength: number; // 0-100
  description: string;
  rvol?: number;
  volume_spike?: boolean;
  breakout?: boolean;
  pct_from_52w_high?: number;
  confluence?: "aligned" | "conflict" | "neutral" | null;
  backtestStats?: BacktestStats;
}

export interface BacktestHorizonStats {
  count: number;
  hit_rate: number;
  avg_return_pct: number;
}

export interface BacktestSideStats {
  signal_days: number;
  horizons: {
    "5": BacktestHorizonStats;
    "20": BacktestHorizonStats;
  };
}

export interface BacktestStats {
  symbol: string;
  period: string;
  bars: number;
  buy: BacktestSideStats;
  sell: BacktestSideStats;
}
