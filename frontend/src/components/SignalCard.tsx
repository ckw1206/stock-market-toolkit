import { TrendingUp, TrendingDown, Minus, X, LineChart, BarChart3, Wallet, Download } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Signal, SignalDirection, SignalType, BacktestStats } from "@/types";
import { fmt } from "@/lib/format";
import { exportCsv } from "@/lib/csv";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SignalCardProps {
  signal: Signal;
  /** When true, analysis data is not available for this tracked symbol. */
  pending?: boolean;
  onDismiss?: (id: string) => void;
  onRemoveTicker?: (symbol: string) => void;
  onView?: (symbol: string) => void;
  onCompare?: (symbol: string) => void;
  onPaperTrade?: (symbol: string) => void;
}

const DIRECTION_ICON = { bullish: TrendingUp, bearish: TrendingDown, neutral: Minus };
const DIRECTION_CLASS: Record<SignalDirection, string> = {
  bullish: "text-up",
  bearish: "text-down",
  neutral: "text-neutral",
};

const SIGNAL_TYPE_LABELS: Record<SignalType, string> = {
  rsi_oversold: "RSI oversold",
  rsi_overbought: "RSI overbought",
  macd_cross: "MACD cross",
  sma_cross: "SMA cross",
  bb_touch: "Bollinger band",
  volume_spike: "Volume spike",
};

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StrengthBar({ strength }: { strength: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-[60px] overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${strength}%` }} />
      </div>
      <span className="font-mono text-xs tabular-nums text-muted-foreground">{strength}%</span>
    </div>
  );
}

export default function SignalCard({
  signal,
  pending = false,
  onDismiss,
  onRemoveTicker,
  onView,
  onCompare,
  onPaperTrade,
}: SignalCardProps) {
  const { t } = useTranslation();
  const Icon = DIRECTION_ICON[signal.direction];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-3 flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn("size-4", DIRECTION_CLASS[signal.direction])} />
            {onView ? (
              <button
                type="button"
                className="cursor-pointer text-base font-semibold hover:underline"
                onClick={() => onView(signal.symbol)}
              >
                {signal.symbol}
              </button>
            ) : (
              <span className="text-base font-semibold">{signal.symbol}</span>
            )}
            {pending ? (
              <Badge variant="outline">{t("common.signals.noSignal")}</Badge>
            ) : (
              <>
                <Badge variant="secondary">{SIGNAL_TYPE_LABELS[signal.signal_type]}</Badge>
                {signal.breakout && <Badge variant="default">{t("common.signals.breakout")}</Badge>}
                {signal.rvol != null && (
                  <Badge variant={signal.rvol > 2 ? "destructive" : "outline"}>
                    {t("common.signals.rvolBadge", { value: signal.rvol.toFixed(1) })}
                  </Badge>
                )}
                {signal.confluence === "aligned" && (
                  <Badge variant="default">{t("common.signals.confluenceAligned")}</Badge>
                )}
                {signal.confluence === "conflict" && (
                  <Badge variant="destructive">{t("common.signals.confluenceConflict")}</Badge>
                )}
                {signal.divergence === "bullish" && (
                  <Badge variant="default">{t("common.signals.divergenceBullish")}</Badge>
                )}
                {signal.divergence === "bearish" && (
                  <Badge variant="destructive">{t("common.signals.divergenceBearish")}</Badge>
                )}
                {signal.daysToEarnings != null && signal.daysToEarnings <= 5 && (
                  <Badge variant="destructive">
                    {t("common.signals.earningsSoon", { count: signal.daysToEarnings })}
                  </Badge>
                )}
              </>
            )}
          </div>
          <div className="flex items-center gap-1">
            {onView ? (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground"
                onClick={() => onView(signal.symbol)}
                aria-label={t("common.signals.viewOnDashboard")}
              >
                <LineChart />
              </Button>
            ) : null}
            {onCompare ? (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground"
                onClick={() => onCompare(signal.symbol)}
                aria-label={t("common.signals.compareTicker")}
              >
                <BarChart3 />
              </Button>
            ) : null}
            {onPaperTrade ? (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground"
                onClick={() => onPaperTrade(signal.symbol)}
                aria-label={t("common.signals.paperTrade")}
              >
                <Wallet />
              </Button>
            ) : null}
            {onRemoveTicker ? (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground hover:text-destructive"
                onClick={() => onRemoveTicker(signal.symbol)}
                aria-label={t("common.signals.stopTracking")}
              >
                <X />
              </Button>
            ) : onDismiss ? (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground"
                onClick={() => onDismiss(signal.id)}
                aria-label={t("common.signals.dismissSignal")}
              >
                <X />
              </Button>
            ) : null}
          </div>
        </div>

        {pending ? (
          <p className="py-2 text-sm text-muted-foreground">{signal.description}</p>
        ) : (
          <>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="mb-0.5 text-xs uppercase text-muted-foreground">{t("common.fields.price")}</p>
                <p className="font-mono font-semibold tabular-nums">${fmt(signal.price)}</p>
                {signal.pct_from_52w_high != null && (() => {
                  const val = signal.pct_from_52w_high;
                  // No "%" here — the i18n string supplies it
                  const signedVal = `${val >= 0 ? "+" : ""}${val.toFixed(1)}`;
                  return (
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {t("common.signals.pctFrom52wHigh", { value: signedVal })}
                    </p>
                  );
                })()}
              </div>
              <div className="text-right">
                <p className="mb-0.5 text-xs uppercase text-muted-foreground">{t("common.signals.signalStrength")}</p>
                <StrengthBar strength={signal.strength} />
              </div>
            </div>

            <p className="mb-2 text-sm leading-relaxed text-muted-foreground">{signal.description}</p>

            {signal.backtestStats && signal.direction !== "neutral" && (() => {
              const bs = signal.backtestStats;
              const side = signal.direction === "bullish" ? bs.buy : bs.sell;
              if (!side || side.signal_days === 0) return null;
              const h5 = side.horizons["5"];
              const h20 = side.horizons["20"];
              const fmtReturn = (v: number) => (v >= 0 ? `+${v}` : `${v}`);

              const handleExport = () => {
                const rows: BacktestStats[] = [bs];
                exportCsv("backtest_results.csv", rows, [
                  { key: "symbol", label: "Symbol" },
                  { key: "period", label: "Period" },
                  { key: "bars", label: "Bars" },
                ]);
              };

              return (
                <div className="mt-2 rounded border border-primary/10 bg-primary/5 p-2 text-xs">
                  <p className="mb-1 font-medium text-muted-foreground">
                    {t("signals.historicalPerformance.label")}
                  </p>
                  <p className="text-muted-foreground">
                    {t("signals.historicalPerformance.signalCount", { count: side.signal_days })} ·{" "}
                    {t("signals.historicalPerformance.hitRate", { rate: Math.round(h5.hit_rate * 100), horizon: 5 })} ·{" "}
                    {t("signals.historicalPerformance.avgReturn", { return: fmtReturn(h5.avg_return_pct) })}
                  </p>
                  <p className="mt-0.5 text-muted-foreground">
                    {t("signals.historicalPerformance.hitRate", { rate: Math.round(h20.hit_rate * 100), horizon: 20 })} ·{" "}
                    {t("signals.historicalPerformance.avgReturn", { return: fmtReturn(h20.avg_return_pct) })}
                  </p>
                  <p className="mt-1 text-[10px] text-muted-foreground/70">
                    {t("signals.historicalPerformance.disclaimer")}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-1.5 h-6 gap-1 px-1 text-[10px]"
                    onClick={handleExport}
                  >
                    <Download className="size-3" />
                    {t("signals.historicalPerformance.exportCsv")}
                  </Button>
                </div>
              );
            })()}

            <p className="text-xs text-muted-foreground">{formatTime(signal.timestamp)}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
