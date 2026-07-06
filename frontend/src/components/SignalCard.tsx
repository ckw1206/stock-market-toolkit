import { useState } from "react";
import { TrendingUp, TrendingDown, Minus, X, LineChart, BarChart3, Wallet } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Signal, SignalDirection, SignalType } from "@/types";
import { fmt } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface SignalCardProps {
  signal: Signal;
  /** When true, analysis data is not available for this tracked symbol. */
  pending?: boolean;
  note?: string;
  tags?: string[];
  onDismiss?: (id: string) => void;
  onRemoveTicker?: (symbol: string) => void;
  onView?: (symbol: string) => void;
  onCompare?: (symbol: string) => void;
  onPaperTrade?: (symbol: string) => void;
  onSaveNote?: (note: string) => void;
  onSaveTags?: (tags: string[]) => void;
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

function NoteField({
  note,
  onSave,
}: {
  note: string;
  onSave: (note: string) => void;
}) {
  const [value, setValue] = useState(note ?? "");
  return (
    <textarea
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={() => {
        if (value !== (note ?? "")) onSave(value);
      }}
      placeholder="Add a note..."
      rows={1}
      className="w-full resize-none rounded-md border border-transparent bg-transparent px-1 py-0.5 text-sm text-muted-foreground placeholder:text-muted-foreground/60 hover:border-input focus:border-input focus:outline-none"
    />
  );
}

function TagEditor({
  tags,
  onSave,
}: {
  tags: string[];
  onSave: (tags: string[]) => void;
}) {
  const [input, setInput] = useState("");

  const addTag = () => {
    const next = input
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);
    if (next.length === 0) return;
    const merged = Array.from(new Set([...tags, ...next]));
    onSave(merged);
    setInput("");
  };

  const removeTag = (tag: string) => {
    onSave(tags.filter((t) => t !== tag));
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {tags.map((tag) => (
        <Badge key={tag} variant="secondary" className="gap-1 text-xs">
          {tag}
          <button
            type="button"
            onClick={() => removeTag(tag)}
            className="cursor-pointer text-muted-foreground hover:text-destructive"
            aria-label={`Remove tag ${tag}`}
          >
            <X className="size-3" />
          </button>
        </Badge>
      ))}
      <Input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            addTag();
          }
        }}
        onBlur={addTag}
        placeholder="+ tag"
        className="h-6 w-20 border-none bg-transparent px-1 text-xs shadow-none focus-visible:ring-1"
      />
    </div>
  );
}

export default function SignalCard({
  signal,
  pending = false,
  note,
  tags = [],
  onDismiss,
  onRemoveTicker,
  onView,
  onCompare,
  onPaperTrade,
  onSaveNote,
  onSaveTags,
}: SignalCardProps) {
  const { t } = useTranslation();
  const Icon = DIRECTION_ICON[signal.direction];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-3 flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2">
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
          {!pending && (
            <div className="flex flex-wrap gap-1">
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
            </div>
          )}
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
              const side = signal.direction === "bullish"
                ? signal.backtestStats.buy
                : signal.backtestStats.sell;
              if (!side || side.signal_days === 0) return null;
              const h5 = side.horizons["5"];
              const h20 = side.horizons["20"];
              const fmtReturn = (v: number) => (v >= 0 ? `+${v}` : `${v}`);
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
                </div>
              );
            })()}

            <p className="text-xs text-muted-foreground">{formatTime(signal.timestamp)}</p>
          </>
        )}

        {/* Per-symbol notes and tags — rendered below the signal content for all cards */}
        {(onSaveNote || onSaveTags) && (
          <div className="mt-3 flex flex-col gap-1.5 border-t border-border pt-3">
            {onSaveNote && (
              <NoteField
                note={note ?? ""}
                onSave={onSaveNote}
              />
            )}
            {onSaveTags && (
              <TagEditor
                tags={tags}
                onSave={onSaveTags}
              />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}