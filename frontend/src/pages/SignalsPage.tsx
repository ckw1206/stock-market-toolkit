import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Activity, Plus, Loader2, X } from "lucide-react";
import SignalCard from "@/components/SignalCard";
import StatCard from "@/components/common/StatCard";
import SymbolSearch from "@/components/common/SymbolSearch";
import { useWatchlist } from "@/hooks/useWatchlist";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";
import type { Signal, BacktestStats } from "@/types";

type AnalysisResponse = {
  symbol?: string;
  signal?: string;
  confidence?: number;
  reasons?: string[];
  indicators?: {
    bias?: number;
    volume_ratio?: number;
    rvol?: number;
    high_52w?: number;
    low_52w?: number;
    pct_from_52w_high?: number;
    confluence?: "aligned" | "conflict" | "neutral" | null;
    divergence?: "bullish" | "bearish" | null;
    days_to_earnings?: number | null;
  };
  price?: number;
  timestamp?: string;
  volume_spike?: boolean;
  breakout?: boolean;
};

function mapAnalysisToSignal(data: AnalysisResponse, symbolOverride?: string): Signal {
  const sym = symbolOverride ?? data.symbol ?? "";
  const directionMap: Record<string, Signal["direction"]> = {
    BUY: "bullish",
    SELL: "bearish",
    NEUTRAL: "neutral",
  };
  const direction = directionMap[data.signal ?? ""] ?? "neutral";
  const confidence = data.confidence ?? 0.5;
  const reasons = (data.reasons ?? []).join("; ");
  const indicators = data.indicators;
  let signal_type: Signal["signal_type"] = "macd_cross";
  if ((indicators?.bias ?? 0) < -3 || (indicators?.bias ?? 0) > 3) signal_type = "bb_touch";
  else if ((indicators?.volume_ratio ?? 0) > 1.3) signal_type = "volume_spike";

  return {
    id: `sig-${sym}`,
    symbol: sym,
    direction,
    signal_type,
    price: data.price ?? 0,
    timestamp: data.timestamp ?? new Date().toISOString(),
    strength: Math.round(confidence * 100),
    description: `[${data.signal ?? "NEUTRAL"}] ${reasons} — confidence ${(confidence * 100).toFixed(0)}%`,
    rvol: indicators?.rvol,
    volume_spike: data.volume_spike,
    breakout: data.breakout,
    pct_from_52w_high: indicators?.pct_from_52w_high,
    confluence: indicators?.confluence,
    divergence: indicators?.divergence,
    daysToEarnings: indicators?.days_to_earnings,
  } satisfies Signal;
}

/** Placeholder for a tracked symbol whose analysis is unavailable. */
function pendingSignal(symbol: string, reason?: string): Signal {
  return {
    id: `sig-${symbol}-pending`,
    symbol,
    direction: "neutral",
    signal_type: "macd_cross",
    price: 0,
    timestamp: new Date().toISOString(),
    strength: 0,
    description: reason ?? "No signal data available for this symbol yet.",
  };
}

/* ─── Signals Page ─── */
export default function SignalsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    symbols: watchedSymbols,
    add: addToWatchlist,
    remove: removeFromWatchlist,
    isWatched,
    items,
    loading: watchlistLoading,
    error: watchlistError,
    refresh: refreshWatchlist,
  } = useWatchlist();
  const [signals, setSignals] = useState<Signal[]>([]);
  const [signalErrors, setSignalErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [addTickerOpen, setAddTickerOpen] = useState(false);
  const [newTicker, setNewTicker] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [tickerError, setTickerError] = useState("");
  const [addingTicker, setAddingTicker] = useState(false);

  const fetchSignals = useCallback(async () => {
      setLoading(true);
      setFetchError(null);
      const token = localStorage.getItem("access_token");
      try {
        const res = await fetch(
          `${import.meta.env.VITE_API_URL || ""}/api/analysis/signals?symbols=${watchedSymbols.join(",")}&period=3mo`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (res.status === 401) {
          navigate("/login");
          return;
        }
        if (!res.ok) throw new Error(`Failed to fetch signals (HTTP ${res.status})`);
        const raw = await res.json();
        const data = Array.isArray(raw)
          ? { signals: raw as AnalysisResponse[], errors: [] as { symbol: string; error: string }[] }
          : (raw as { signals: AnalysisResponse[]; errors: { symbol: string; error: string }[] });
        const mapped = data.signals.map((d) => mapAnalysisToSignal(d));
        const errs = data.errors ?? [];
        setSignalErrors(Object.fromEntries(errs.map((e) => [e.symbol, e.error])));
        if (errs.length > 0) {
          const failedSymbols = errs.map((e) => e.symbol).join(", ");
          toast.error(t("signals.toast.loadFailed", { symbols: failedSymbols }));
        }

        const backtestResults = await Promise.allSettled(
          mapped.map((signal) =>
            fetch(
              `${import.meta.env.VITE_API_URL || ""}/api/analysis/${signal.symbol}/backtest`,
              { headers: { Authorization: `Bearer ${token}` } },
            ).then((r) => (r.ok ? r.json() : null))
          ),
        );

        const signalsWithBacktest = mapped.map((signal, i) => {
          const result = backtestResults[i];
          if (result.status === "fulfilled" && result.value != null) {
            return { ...signal, backtestStats: result.value as BacktestStats };
          }
          return signal;
        });

        setSignals(signalsWithBacktest);
      } catch (err) {
        setSignals([]);
        setSignalErrors({});
        const msg = err instanceof Error ? err.message : "Failed to fetch signals";
        setFetchError(msg);
        toast.error(t("signals.toast.batchLoadFailed"));
      } finally {
        setLoading(false);
      }
    }, [watchedSymbols, t, navigate]);

  useEffect(() => {
    if (watchedSymbols.length === 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- false positive: early-return guard
      setSignals((prev) => (prev.length === 0 ? prev : []));
      setSignalErrors({});
      setFetchError(null);
      setLoading(false);
      return;
    }
    fetchSignals();
  }, [watchedSymbols, fetchSignals]);

  const fetchSignalForTicker = useCallback(async (symbol: string): Promise<Signal> => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(
      `${import.meta.env.VITE_API_URL || ""}/api/analysis/${symbol}?period=1mo`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (!res.ok) {
      let detail = t("signals.noSignalDataFor", { symbol });
      try {
        detail = (await res.json())?.detail ?? detail;
      } catch {
        // non-JSON error body — keep the default reason
      }
      throw new Error(detail);
    }
    const data = (await res.json()) as AnalysisResponse;
    return {
      ...mapAnalysisToSignal(data, symbol),
      id: `sig-${symbol}-${Date.now()}`,
    };
  }, [t]);

  const handleAddTicker = async () => {
    const trimmed = (selectedSymbol || newTicker).trim().toUpperCase();
    if (!trimmed) {
      setTickerError(t("signals.addTicker.errorRequired"));
      return;
    }
    if (!/^[A-Z0-9]{1,10}(\.[A-Z]{1,2})?$/.test(trimmed)) {
      setTickerError(t("signals.addTicker.errorInvalidFormat"));
      return;
    }
    if (isWatched(trimmed)) {
      setTickerError(t("signals.addTicker.errorAlreadyTracked", { symbol: trimmed }));
      return;
    }

    setTickerError("");
    setAddingTicker(true);

    try {
      await addToWatchlist(trimmed);
    } catch {
      toast.error(t("signals.toast.addFailed", { symbol: trimmed }));
      setAddingTicker(false);
      return;
    }

    // The symbol is now tracked regardless of whether analysis is available,
    // so close the dialog and surface any signal reason on the card itself.
    setAddTickerOpen(false);
    setNewTicker("");
    setSelectedSymbol("");

    try {
      const signal = await fetchSignalForTicker(trimmed);
      setSignals((prev) => [...prev, signal]);
      setSignalErrors((prev) => {
        if (!(trimmed in prev)) return prev;
        const next = { ...prev };
        delete next[trimmed];
        return next;
      });
      toast.success(t("signals.toast.added", { symbol: trimmed }));
    } catch (err) {
      const reason = err instanceof Error ? err.message : t("signals.analysisUnavailable");
      setSignalErrors((prev) => ({ ...prev, [trimmed]: reason }));
      toast(t("signals.toast.addedNoData", { symbol: trimmed }));
    } finally {
      setAddingTicker(false);
    }
  };

  const handleRemoveTicker = useCallback(async (symbol: string) => {
    await removeFromWatchlist(symbol);
    setSignals((prev) => prev.filter((s) => s.symbol !== symbol));
    setSignalErrors((prev) => {
      if (!(symbol in prev)) return prev;
      const next = { ...prev };
      delete next[symbol];
      return next;
    });
    toast(t("signals.toast.removed", { symbol }));
  }, [removeFromWatchlist, t]);

  const handleView = useCallback((symbol: string) => navigate(`/?symbol=${symbol}`), [navigate]);
  const handleCompare = useCallback(
    (symbol: string) => navigate(`/compare?symbols=${symbol}`),
    [navigate],
  );

  // Single source of truth: every tracked symbol shows up, carrying its signal
  // when analysis is available and a placeholder otherwise.
  const signalBySymbol = useMemo(
    () => new Map(signals.map((s) => [s.symbol, s])),
    [signals],
  );
  const trackedSignals = useMemo(
    () =>
      items.map((item) => ({
        signal:
          signalBySymbol.get(item.symbol) ??
          pendingSignal(item.symbol, signalErrors[item.symbol] ?? t("signals.noSignalData")),
        pending: !signalBySymbol.has(item.symbol),
      })),
    [items, signalBySymbol, signalErrors, t],
  );

  const bullish = signals.filter((s) => s.direction === "bullish");
  const bearish = signals.filter((s) => s.direction === "bearish");
  const neutral = signals.filter((s) => s.direction === "neutral");

  const showSkeleton = (loading || watchlistLoading) && items.length === 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t("signals.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("signals.subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => { refreshWatchlist(); fetchSignals(); }} disabled={watchlistLoading}>
            {watchlistLoading ? <Loader2 className="mr-1 size-4 animate-spin" /> : null}
            {t("signals.refresh")}
          </Button>
          <Button onClick={() => setAddTickerOpen(true)} variant="outline" size="sm">
            <Plus className="size-4" />
            {t("signals.addTicker.button")}
          </Button>
        </div>
      </div>

      {watchlistError && <p className="text-sm text-destructive">{watchlistError}</p>}
      {fetchError && (
        <div className="flex items-center justify-between gap-2 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <span>{fetchError}</span>
          <button
            onClick={() => setFetchError(null)}
            className="shrink-0 rounded p-1 hover:bg-destructive/20"
            aria-label="Dismiss error"
          >
            <X className="size-4" />
          </button>
        </div>
      )}

      <Dialog open={addTickerOpen} onOpenChange={setAddTickerOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("signals.addTicker.title")}</DialogTitle>
            <DialogDescription>
              {t("signals.addTicker.description")}
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <SymbolSearch
              value={selectedSymbol}
              onSearch={(sym) => {
                setSelectedSymbol(sym);
                setNewTicker(sym);
                setTickerError("");
              }}
            />
            {tickerError && (
              <p className="mt-2 text-sm text-destructive">{tickerError}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddTickerOpen(false)}>
              {t("signals.addTicker.cancel")}
            </Button>
            <Button onClick={handleAddTicker} disabled={addingTicker}>
              {addingTicker ? t("signals.addTicker.adding") : t("signals.addTicker.button")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {showSkeleton ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Skeleton className="h-[76px] rounded-xl" />
            <Skeleton className="h-[76px] rounded-xl" />
            <Skeleton className="h-[76px] rounded-xl" />
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-[180px] rounded-xl" />
            ))}
          </div>
        </>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label={t("signals.stats.bullish")} value={String(bullish.length)} tone="up" />
            <StatCard label={t("signals.stats.bearish")} value={String(bearish.length)} tone="down" />
            <StatCard label={t("signals.stats.neutral")} value={String(neutral.length)} tone="neutral" />
          </div>

          {items.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                <Activity className="size-8 text-muted-foreground" />
                <p className="text-muted-foreground">{t("signals.empty.title")}</p>
                <p className="text-sm text-muted-foreground">
                  {t("signals.empty.description")}
                </p>
                <Button variant="outline" size="sm" onClick={() => setAddTickerOpen(true)}>
                  <Plus className="mr-1 size-4" />
                  {t("signals.addTicker.button")}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {trackedSignals.map(({ signal, pending }) => (
                <SignalCard
                  key={signal.symbol}
                  signal={signal}
                  pending={pending}
                  onRemoveTicker={handleRemoveTicker}
                  onView={handleView}
                  onCompare={handleCompare}
                />
              ))}
            </div>
          )}

          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
            <p className="m-0 text-xs text-muted-foreground">
              <strong>{t("signals.disclaimer.label")}</strong> {t("signals.disclaimer.body")}
            </p>
          </div>
        </>
      )}
    </div>
  );
}