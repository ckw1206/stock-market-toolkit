import { SignalCard } from "frontend";

const noop = () => {};
const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString();

const bullish = {
  id: "sig-1",
  symbol: "AAPL",
  direction: "bullish" as const,
  signal_type: "rsi_oversold" as const,
  price: 232.14,
  timestamp: hoursAgo(2),
  strength: 78,
  description:
    "RSI recovered from oversold territory while price reclaimed the 50-day SMA — a momentum reversal with volume confirmation.",
  rvol: 2.4,
  breakout: true,
  pct_from_52w_high: -4.2,
  confluence: "aligned" as const,
  divergence: "bullish" as const,
  backtestStats: {
    symbol: "AAPL",
    buy: {
      signal_days: 42,
      horizons: {
        "5": { count: 42, hit_rate: 0.64, avg_return_pct: 1.8 },
        "20": { count: 42, hit_rate: 0.71, avg_return_pct: 4.6 },
      },
    },
  },
};

const bearish = {
  id: "sig-2",
  symbol: "TSLA",
  direction: "bearish" as const,
  signal_type: "macd_cross" as const,
  price: 412.9,
  timestamp: hoursAgo(6),
  strength: 55,
  description:
    "MACD crossed below its signal line beneath the zero line, with relative volume fading — bearish momentum building.",
  rvol: 1.1,
  pct_from_52w_high: -18.6,
};

export const Bullish = () => (
  <div className="bg-background text-foreground p-6 w-[360px]">
    <SignalCard signal={bullish} onView={noop} onCompare={noop} onDismiss={noop} />
  </div>
);

export const Bearish = () => (
  <div className="bg-background text-foreground p-6 w-[360px]">
    <SignalCard signal={bearish} onView={noop} onPaperTrade={noop} onDismiss={noop} />
  </div>
);
