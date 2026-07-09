import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Star } from "lucide-react";
import { getStock } from "@/api/stockApi";
import { useWatchlist } from "@/hooks/useWatchlist";
import SymbolSearch from "@/components/common/SymbolSearch";
import { fmt, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Quote {
  price: number;
  changePct: number;
}

// One quote per watched symbol. There's no batch-quote endpoint, so reuse
// getStock per symbol (short range is enough for last close + day change).
function useWatchlistQuotes(symbols: string[]) {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const key = symbols.join(",");
  useEffect(() => {
    if (!symbols.length) return;
    let cancelled = false;
    (async () => {
      const results = await Promise.allSettled(symbols.map((s) => getStock(s, "5d")));
      if (cancelled) return;
      const next: Record<string, Quote> = {};
      results.forEach((r, i) => {
        if (r.status !== "fulfilled") return;
        const close = r.value.close;
        const last = close[close.length - 1];
        const prev = close[close.length - 2] ?? last;
        if (last == null) return;
        next[symbols[i]] = { price: last, changePct: prev ? ((last - prev) / prev) * 100 : 0 };
      });
      setQuotes(next);
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- key derives from symbols
  }, [key]);
  return quotes;
}

export default function WatchlistSidebar({
  activeSymbol,
  onSelect,
  compact = false,
}: {
  activeSymbol: string;
  onSelect: (symbol: string) => void;
  compact?: boolean;
}) {
  const { t } = useTranslation();
  const { items, add } = useWatchlist();
  const symbols = items.map((i) => i.symbol);
  const quotes = useWatchlistQuotes(symbols);

  const handleAdd = async (symbol: string) => {
    try {
      await add(symbol);
    } catch {
      // silent — already watched or request failed
    }
    onSelect(symbol);
  };

  return (
    <aside className="w-full min-[900px]:sticky min-[900px]:top-[76px] min-[900px]:w-[280px] min-[900px]:flex-none">
      <div className="flex max-h-[260px] flex-col overflow-hidden rounded-xl border bg-card min-[900px]:max-h-[calc(100vh-96px)]">
        <div className="flex flex-none items-center justify-between border-b px-4 py-3">
          <span className="text-sm font-semibold">{t("dashboard.watchlist.title")}</span>
          <span className="text-xs text-muted-foreground">{t("dashboard.watchlist.count", { count: items.length })}</span>
        </div>

        <div className="flex flex-col gap-0.5 overflow-y-auto p-2">
          {items.length === 0 && (
            <p className="px-2 py-6 text-center text-xs text-muted-foreground">{t("dashboard.watchlist.empty")}</p>
          )}
          {items.map((item) => {
            const q = quotes[item.symbol];
            const active = item.symbol === activeSymbol;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect(item.symbol)}
                className={cn(
                  "flex items-center gap-2 rounded-lg text-left",
                  compact ? "px-2 py-1" : "p-2",
                  active ? "bg-secondary" : "hover:bg-secondary/50",
                )}
              >
                <Star className="size-3.5 shrink-0 fill-yellow-500 text-yellow-500" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-semibold">{item.symbol}</div>
                  {!compact && item.note && (
                    <div className="truncate text-xs text-muted-foreground">{item.note}</div>
                  )}
                </div>
                <div className="text-right">
                  <div className="font-mono text-xs font-semibold tabular-nums">
                    {q ? `$${fmt(q.price)}` : "—"}
                  </div>
                  <div className={cn("font-mono text-xs tabular-nums", !q ? "text-muted-foreground" : q.changePct >= 0 ? "text-up" : "text-down")}>
                    {q ? pct(q.changePct) : ""}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="flex-none border-t p-2">
          <SymbolSearch onSearch={handleAdd} />
        </div>
      </div>
    </aside>
  );
}
