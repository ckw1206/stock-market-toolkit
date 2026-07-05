import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { getMarketBreadth, type BreadthData } from "@/api/stockApi";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface BreadthCardProps {
  className?: string;
}

const REGIME_ICON = { risk_on: TrendingUp, risk_off: TrendingDown, neutral: Minus };
const REGIME_CLASS: Record<BreadthData["regime"], string> = {
  risk_on: "text-up",
  risk_off: "text-down",
  neutral: "text-neutral",
};
const REGIME_BADGE_VARIANT: Record<BreadthData["regime"], "default" | "destructive" | "secondary"> = {
  risk_on: "default",
  risk_off: "destructive",
  neutral: "secondary",
};

function Stat({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[11px] uppercase text-muted-foreground">{label}</span>
      <span className={cn("font-mono text-sm font-semibold tabular-nums", className)}>{value}</span>
    </div>
  );
}

function PctBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary"
            style={{ width: `${value}%` }}
          />
        </div>
        <span className="w-8 text-right font-mono text-xs tabular-nums text-muted-foreground">
          {value.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

export default function BreadthCard({ className }: BreadthCardProps) {
  const { t } = useTranslation();
  const [breadth, setBreadth] = useState<BreadthData[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      setBreadth(await getMarketBreadth());
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

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader className="px-4 pb-3 pt-4">
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent className="px-4 pb-4 pt-0">
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  const latest = breadth && breadth.length > 0 ? breadth[0] : null;
  const Icon = latest ? REGIME_ICON[latest.regime] : Minus;

  return (
    <Card className={className}>
      <CardHeader className="px-4 pb-3 pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn("size-4", latest ? REGIME_CLASS[latest.regime] : "text-neutral")} />
            <div className="text-sm font-medium">{t("dashboard.breadth.title")}</div>
            {latest && (
              <Badge variant={REGIME_BADGE_VARIANT[latest.regime]} className="text-[10px]">
                {t(`dashboard.breadth.regime.${latest.regime}`)}
              </Badge>
            )}
          </div>
          <Button variant="ghost" size="icon" className="size-6" onClick={fetchData}>
            <RefreshCw className="size-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        {error || !latest ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            {error ?? t("dashboard.breadth.empty")}
          </p>
        ) : (
          <div className="space-y-3">
            {/* Row 1: % Above 50-DMA and % Above 200-DMA */}
            <div className="grid grid-cols-2 gap-3">
              <PctBar label={t("dashboard.breadth.aboveSma50")} value={latest.pct_above_50dma} />
              <PctBar label={t("dashboard.breadth.aboveSma200")} value={latest.pct_above_200dma} />
            </div>

            {/* Row 2: Advancers vs Decliners */}
            <div className="grid grid-cols-2 gap-3">
              <Stat
                label={t("dashboard.breadth.advancers")}
                value={String(latest.advancers)}
                className="text-up"
              />
              <Stat
                label={t("dashboard.breadth.decliners")}
                value={String(latest.decliners)}
                className="text-down"
              />
            </div>

            {/* Row 3: 52W Highs vs 52W Lows */}
            <div className="grid grid-cols-2 gap-3">
              <Stat label={t("dashboard.breadth.newHighs")} value={String(latest.new_highs)} />
              <Stat label={t("dashboard.breadth.newLows")} value={String(latest.new_lows)} />
            </div>

            {/* Footer: regime badge + date */}
            <div className="flex items-center justify-between pt-1">
              {latest.regime && (
                <Badge variant={REGIME_BADGE_VARIANT[latest.regime]} className="text-[10px]">
                  {t(`dashboard.breadth.regime.${latest.regime}`)}
                </Badge>
              )}
              <span className="ml-auto text-xs text-muted-foreground">{latest.date}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}