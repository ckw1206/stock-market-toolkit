import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { RefreshCw } from "lucide-react";
import { getTopSignals, type TopSignalsData, type TopSignalItem } from "@/api/stockApi";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function relativeScan(timestamp: string | null): string {
  if (!timestamp) return "—";
  const mins = Math.floor((Date.now() - new Date(timestamp).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

// Grouped buy/sell chip strip. Chips wrap to a new line rather than scrolling
// horizontally (deliberate — see design handoff).
function ChipGroup({
  label,
  tone,
  items,
  onView,
}: {
  label: string;
  tone: "up" | "down";
  items: TopSignalItem[];
  onView: (symbol: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="flex min-w-0 flex-1 basis-[240px] flex-wrap items-center gap-2">
      <span
        className={cn(
          "flex-none rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide",
          tone === "up" ? "bg-up text-up-foreground" : "bg-down text-down-foreground",
        )}
      >
        {label} · {items.length}
      </span>
      {items.map((item) => (
        <button
          key={item.symbol}
          type="button"
          onClick={() => onView(item.symbol)}
          className="flex flex-none items-center gap-1.5 rounded-full px-2.5 py-1"
          style={{ background: tone === "up" ? "hsl(var(--up) / 0.14)" : "hsl(var(--down) / 0.14)" }}
        >
          <span className="text-xs font-semibold">{item.symbol}</span>
          <span className={cn("font-mono text-xs font-semibold tabular-nums", tone === "up" ? "text-up" : "text-down")}>
            {(item.confidence * 100).toFixed(0)}%
          </span>
        </button>
      ))}
    </div>
  );
}

export default function TopSignalsStrip() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState<TopSignalsData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      setData(await getTopSignals(10));
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- non-critical fetch
    fetchData();
  }, []);

  const hasData = data && (data.buys.length > 0 || data.sells.length > 0);

  return (
    <div className="rounded-xl border bg-card px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold">{t("dashboard.topSignals.title")}</span>
          <span className="text-xs text-muted-foreground">
            {t("dashboard.topSignals.lastScanShort")} {data ? relativeScan(data.scanned_at) : "—"}
          </span>
        </div>
        <Button variant="ghost" size="icon" className="size-6" onClick={fetchData} aria-label={t("dashboard.retry")}>
          <RefreshCw className={cn("size-3", loading && "animate-spin")} />
        </Button>
      </div>
      {loading && !data ? (
        <Skeleton className="h-7 w-full" />
      ) : !hasData ? (
        // A completed scan with zero buys/sells means "all HOLD today", not "broken".
        <p className="py-1 text-center text-xs text-muted-foreground">
          {t(data?.scanned_at ? "signals.scanEmpty.allHold" : "signals.scanEmpty.title")}
        </p>
      ) : (
        <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2">
          <ChipGroup label={t("dashboard.topSignals.buy")} tone="up" items={data.buys} onView={(s) => navigate(`/?symbol=${s}`)} />
          <ChipGroup label={t("dashboard.topSignals.sell")} tone="down" items={data.sells} onView={(s) => navigate(`/?symbol=${s}`)} />
        </div>
      )}
    </div>
  );
}
