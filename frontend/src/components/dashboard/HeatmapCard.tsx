import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { RefreshCw } from "lucide-react";
import { getHeatmap, type HeatmapData, type HeatmapSymbol } from "@/api/stockApi";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

interface HeatmapCardProps {
  className?: string;
}

// Diverging polarity: up/down theme tokens with alpha buckets by |move|;
// the neutral midpoint stays on the muted surface. Signed % is always
// printed on the tile so the value is never conveyed by color alone.
function tileBackground(pct: number | null): string | undefined {
  if (pct == null || pct === 0) return undefined;
  const token = pct > 0 ? "--up" : "--down";
  const mag = Math.abs(pct);
  const alpha = mag >= 3 ? 0.45 : mag >= 1 ? 0.28 : 0.14;
  return `hsl(var(${token}) / ${alpha})`;
}

function Tile({ item, onView }: { item: HeatmapSymbol; onView: (symbol: string) => void }) {
  const pct = item.pct_change_1d;
  return (
    <button
      type="button"
      onClick={() => onView(item.symbol)}
      className="flex min-w-0 cursor-pointer flex-col rounded-md bg-muted px-2 py-1.5 text-left hover:ring-2 hover:ring-ring"
      style={{ backgroundColor: tileBackground(pct) }}
      title={item.price != null ? `${item.symbol} $${item.price.toFixed(2)}` : item.symbol}
    >
      <span className="truncate text-xs font-semibold">{item.symbol}</span>
      <span className="font-mono text-xs tabular-nums text-muted-foreground">
        {pct != null ? `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%` : "—"}
      </span>
    </button>
  );
}

export default function HeatmapCard({ className }: HeatmapCardProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState<HeatmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getHeatmap());
    } catch (err) {
      setError(err instanceof Error ? err.message : t("dashboard.failedToLoad"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- non-critical state update for data fetch
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fetchData is stable and has no external deps
  }, []);

  const handleView = (symbol: string) => {
    navigate(`/?symbol=${symbol}`);
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader className="px-4 pb-3 pt-4">
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent className="px-4 pb-4 pt-0">
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  const empty = !data || error || data.sectors.length === 0;

  return (
    <Card className={className}>
      <CardHeader className="px-4 pb-3 pt-4">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">{t("dashboard.heatmap.title")}</div>
          <Button variant="ghost" size="icon" className="size-6" onClick={fetchData}>
            <RefreshCw className="size-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        {empty ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            {t("dashboard.heatmap.empty")}
          </p>
        ) : (
          <div className="max-h-[240px] space-y-3 overflow-y-auto">
            {data.sectors.map((sector) => (
              <div key={sector.sector}>
                <p className="mb-1 text-xs uppercase text-muted-foreground">
                  {sector.sector === "Other" ? t("dashboard.heatmap.otherSector") : sector.sector}
                </p>
                <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-4">
                  {sector.symbols.map((item) => (
                    <Tile key={item.symbol} item={item} onView={handleView} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
