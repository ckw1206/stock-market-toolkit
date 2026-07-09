import { useState, useEffect, useMemo, startTransition, lazy, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { LayoutGrid, List } from "lucide-react";
import { getStock, getIndicators, getStockInfo, getFundamentals, getDividends, getNews, getTopSignals } from "@/api/stockApi";
import type { TopSignalsData } from "@/api/stockApi";
import type { StockData, Indicators, StockInfo, Fundamentals, DividendData, NewsData } from "@/types";
import { TIMEFRAMES } from "@/types";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleBar, MultiToggleBar } from "@/components/common/ToggleBar";
import SymbolSearch from "@/components/common/SymbolSearch";
import DashboardGrid from "@/components/dashboard/DashboardGrid";
import WatchlistSidebar from "@/components/dashboard/WatchlistSidebar";

const EditableGrid = lazy(() => import("@/components/dashboard/EditableGrid"));

const LAST_SYMBOL_KEY = "dashboard.lastSymbol";

const TIMEFRAME_OPTIONS = TIMEFRAMES.map((t) => ({ value: t.value, label: t.label }));
const INDICATOR_OPTIONS = [
  { value: "sma20", label: "SMA 20" },
  { value: "sma50", label: "SMA 50" },
  { value: "sma200", label: "SMA 200" },
  { value: "ema12", label: "EMA 12" },
  { value: "ema26", label: "EMA 26" },
  { value: "rsi", label: "RSI" },
  { value: "macd", label: "MACD" },
  { value: "bb", label: "Bollinger" },
];

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-4">
      <Skeleton className="col-span-12 h-[340px] rounded-xl" />
      <Skeleton className="col-span-12 h-[160px] rounded-xl lg:col-span-6" />
      <Skeleton className="col-span-12 h-[160px] rounded-xl lg:col-span-6" />
      <Skeleton className="col-span-12 h-[480px] rounded-xl lg:col-span-4" />
      <Skeleton className="col-span-12 h-[480px] rounded-xl lg:col-span-8" />
    </div>
  );
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [symbol, setSymbol] = useState(() =>
    searchParams.get("symbol")?.toUpperCase()
    || localStorage.getItem(LAST_SYMBOL_KEY)
    || "AAPL"
  );
  const [period, setPeriod] = useState("1mo");
  const [stock, setStock] = useState<StockData | null>(null);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [info, setInfo] = useState<StockInfo | null>(null);
  const [fundamentals, setFundamentals] = useState<Fundamentals | null>(null);
  const [dividends, setDividends] = useState<DividendData | null>(null);
  const [news, setNews] = useState<NewsData | null>(null);
  const [newsLoading, setNewsLoading] = useState(false);
  const [topSignals, setTopSignals] = useState<TopSignalsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [active, setActive] = useState<string[]>(["sma20", "rsi", "macd"]);
  const [editMode, setEditMode] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  // Fetch on symbol/period change. `loading` is raised in the change handlers
  // so this effect performs no synchronous setState (only after the await).
  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- newsLoading is non-critical state raised before an async fetch
    setNewsLoading(true);
    (async () => {
      try {
        // Core data must load for the dashboard to render. Fundamentals and
        // dividends are secondary: many symbols (e.g. ETFs like 0050.TW) have no
        // fundamentals and return 404, which must NOT fail the whole dashboard.
        const [st, ind, inf, fund, divs] = await Promise.all([
          getStock(symbol, period),
          getIndicators(symbol, period),
          getStockInfo(symbol),
          getFundamentals(symbol).catch(() => null),
          getDividends(symbol).catch(() => null),
        ]);
        if (cancelled) return;
        let newsData: NewsData | null = null;
        try {
          newsData = await getNews(symbol);
        } catch {
          // News is non-critical — don't crash the dashboard if it fails
        }
        if (cancelled) return;
        startTransition(() => {
          setStock(st);
          setIndicators(ind);
          setInfo(inf);
          setFundamentals(fund);
          setDividends(divs);
          setNews(newsData);
          setError("");
        });
      } catch (e: unknown) {
        if (cancelled) return;
        setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("dashboard.failedToLoad"));
        setStock(null);
        setIndicators(null);
        setInfo(null);
        setFundamentals(null);
        setDividends(null);
        setNews(null);
      } finally {
        if (!cancelled) {
          setLoading(false);
          setNewsLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [symbol, period, reloadKey, t]);

  const onSymbol = (s: string) => {
    if (s !== symbol) {
      setLoading(true);
      setSymbol(s);
      localStorage.setItem(LAST_SYMBOL_KEY, s);
    }
  };
  const onPeriod = (p: string) => { if (p !== period) { setLoading(true); setPeriod(p); } };
  const retry = () => { setLoading(true); setReloadKey((k) => k + 1); };

  useEffect(() => {
    getTopSignals(10)
      .then(setTopSignals)
      .catch(() => setTopSignals(null));
  }, []);

  const activeSet = useMemo(() => new Set(active), [active]);
  const ready = Boolean(stock && indicators && info);

  return (
    <div className="flex flex-wrap items-start gap-5">
      <WatchlistSidebar activeSymbol={symbol} onSelect={onSymbol} />

      <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <SymbolSearch value={symbol} onSearch={onSymbol} loading={loading} />
          <ToggleBar ariaLabel={t("dashboard.timeframe")} options={TIMEFRAME_OPTIONS} value={period} onChange={onPeriod} />
          <Button
            variant={editMode ? "secondary" : "outline"}
            size="sm"
            className="ml-auto gap-2"
            onClick={() => setEditMode((v) => !v)}
          >
            {editMode ? <List /> : <LayoutGrid />}
            {editMode ? t("dashboard.done") : t("dashboard.editLayout")}
          </Button>
        </div>

        <MultiToggleBar ariaLabel={t("dashboard.indicators")} options={INDICATOR_OPTIONS} value={active} onChange={setActive} />

        {error && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading && !ready ? (
          <DashboardSkeleton />
        ) : ready && stock && indicators && info ? (
          editMode ? (
            <Suspense fallback={<DashboardSkeleton />}>
              <EditableGrid stock={stock} indicators={indicators} info={info} fundamentals={fundamentals} dividends={dividends} news={news} newsLoading={newsLoading} active={activeSet} topSignals={topSignals} />
            </Suspense>
          ) : (
            <DashboardGrid stock={stock} indicators={indicators} info={info} fundamentals={fundamentals} dividends={dividends} news={news} newsLoading={newsLoading} active={activeSet} topSignals={topSignals} />
          )
        ) : (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed py-16 text-center text-sm text-muted-foreground">
            <p>{error ? t("dashboard.couldntLoadSymbol") : t("dashboard.noData")}</p>
            <Button variant="outline" size="sm" onClick={retry}>{t("dashboard.retry")}</Button>
          </div>
        )}
      </div>
    </div>
  );
}
