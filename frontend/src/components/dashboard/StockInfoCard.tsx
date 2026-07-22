import { useTranslation } from "react-i18next";
import type { StockData, StockInfo } from "@/types";
import { fmt, pct, volFmt, compactUsd } from "@/lib/format";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import StatCard, { type StatTone } from "@/components/common/StatCard";
import { cn } from "@/lib/utils";

export default function StockInfoCard({ info, stock, className }: { info: StockInfo; stock: StockData; className?: string }) {
  const { t } = useTranslation();
  // Day change is always today's move vs the official previous close, never the
  // last chart bar (whose interval varies by period: 5m for 1d, 15m for 5d…).
  const currentPrice = info.price ?? stock.close[stock.close.length - 1];
  const prevPrice = info.previous_close ?? stock.close[stock.close.length - 2] ?? currentPrice;
  const priceChange = currentPrice - prevPrice;
  const priceChangePct = prevPrice ? (priceChange / prevPrice) * 100 : 0;
  const tone: StatTone = priceChange >= 0 ? "up" : "down";

  const highs = stock.high.filter((v): v is number => v != null);
  const lows = stock.low.filter((v): v is number => v != null);

  const stats: { label: string; value: string; tone?: StatTone }[] = [
    { label: t("common.fields.currentPrice"), value: `$${fmt(currentPrice)}` },
    { label: t("common.fields.dayChange"), value: pct(priceChangePct), tone },
    { label: t("common.fields.periodHigh"), value: highs.length ? `$${fmt(Math.max(...highs))}` : "—" },
    { label: t("common.fields.periodLow"), value: lows.length ? `$${fmt(Math.min(...lows))}` : "—" },
    { label: t("common.fields.volume"), value: volFmt(stock.volume[stock.volume.length - 1]) },
    { label: t("common.fields.avgVolume"), value: volFmt(info.avg_volume) },
    { label: t("common.fields.marketCap"), value: compactUsd(info.market_cap) },
    { label: t("common.fields.peRatio"), value: info.trailing_pe != null ? fmt(info.trailing_pe) : "—" },
    { label: t("common.fields.forwardPe"), value: info.forward_pe != null ? fmt(info.forward_pe) : "—" },
    { label: t("common.fields.dividendYield"), value: info.dividend_yield != null ? `${(info.dividend_yield * 100).toFixed(2)}%` : "—" },
    { label: t("common.fields.beta"), value: info.beta != null ? fmt(info.beta) : "—" },
    { label: t("common.fields.week52High"), value: info.week_52_high != null ? `$${fmt(info.week_52_high)}` : "—" },
    { label: t("common.fields.week52Low"), value: info.week_52_low != null ? `$${fmt(info.week_52_low)}` : "—" },
    { label: t("common.fields.sector"), value: info.sector || "—" },
    { label: t("common.fields.industry"), value: info.industry || "—" },
  ];

  return (
    <Card className={cn("flex h-full flex-col overflow-hidden", className)}>
      <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0 px-4 pb-3 pt-4">
        <div className="min-w-0">
          <div className="text-lg font-semibold">{info.symbol}</div>
          <div className="truncate text-xs text-muted-foreground">{info.long_name || info.short_name || info.symbol}</div>
        </div>
        <div className="text-right">
          <div className="font-mono text-lg font-semibold tabular-nums">${fmt(currentPrice)}</div>
          <div className={cn("font-mono text-xs tabular-nums", priceChange >= 0 ? "text-up" : "text-down")}>
            {priceChange >= 0 ? "▲" : "▼"} {fmt(Math.abs(priceChange))} ({pct(priceChangePct)})
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col px-4 pb-4 pt-0">
        <div className="stk-scroll flex-1 overflow-y-auto">
          <div className="grid grid-cols-2 gap-2">
            {stats.map((s) => (
              <StatCard key={s.label} label={s.label} value={s.value} tone={s.tone} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
