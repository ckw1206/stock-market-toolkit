import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, YAxis } from "recharts";
import { getMarketBreadth, type MarketBreadthData } from "@/api/stockApi";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface BreadthCardProps {
  className?: string;
}

const REGIME_ICON = { risk_on: TrendingUp, risk_off: TrendingDown, neutral: Minus };
const REGIME_CLASS: Record<MarketBreadthData["regime"], string> = {
  risk_on: "text-up",
  risk_off: "text-down",
  neutral: "text-neutral",
};
const REGIME_BADGE_VARIANT: Record<MarketBreadthData["regime"], "default" | "destructive" | "secondary"> = {
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

export default function BreadthCard({ className }: BreadthCardProps) {
  const { t } = useTranslation();
  const [data, setData] = useState<MarketBreadthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getMarketBreadth());
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

  const hasData = data != null && data.scanned_at != null;
  const Icon = data ? REGIME_ICON[data.regime] : Minus;

  return (
    <Card className={className}>
      <CardHeader className="px-4 pb-3 pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn("size-4", data ? REGIME_CLASS[data.regime] : "text-neutral")} />
            <div className="text-sm font-medium">{t("dashboard.breadth.title")}</div>
            {hasData && (
              <Badge variant={REGIME_BADGE_VARIANT[data.regime]} className="text-[10px]">
                {t(`dashboard.breadth.regime.${data.regime}`)}
              </Badge>
            )}
          </div>
          <Button variant="ghost" size="icon" className="size-6" onClick={fetchData}>
            <RefreshCw className="size-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        {error || !hasData ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            {error ?? t("dashboard.breadth.empty")}
          </p>
        ) : (
          <>
            <div className="grid grid-cols-4 gap-2">
              <Stat
                label={t("dashboard.breadth.aboveSma50")}
                value={data.pct_above_sma50 != null ? `${data.pct_above_sma50.toFixed(0)}%` : "—"}
              />
              <Stat label={t("dashboard.breadth.advancers")} value={String(data.advancers)} className="text-up" />
              <Stat label={t("dashboard.breadth.decliners")} value={String(data.decliners)} className="text-down" />
              <Stat label={t("dashboard.breadth.newHighs")} value={String(data.new_highs)} />
            </div>
            {data.history.length > 1 && (
              <div className="mt-3 h-12 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.history} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                    <YAxis domain={[0, 100]} hide />
                    <Area
                      type="monotone"
                      dataKey="pct_above_sma50"
                      stroke="hsl(var(--primary))"
                      fill="hsl(var(--primary) / 0.15)"
                      strokeWidth={1.5}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
