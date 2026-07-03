import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { TrendingUp, TrendingDown, Minus, RefreshCw, Info } from "lucide-react";
import { getTopSignals, type TopSignalsData, type TopSignalItem } from "@/api/stockApi";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface TopSignalsCardProps {
  className?: string;
}

function SignalRow({ item, onView }: { item: TopSignalItem; onView: (symbol: string) => void }) {
  const { t } = useTranslation();
  const Icon = item.signal === "BUY" ? TrendingUp : item.signal === "SELL" ? TrendingDown : Minus;
  const iconClass = item.signal === "BUY" ? "text-up" : item.signal === "SELL" ? "text-down" : "text-neutral";

  return (
    <div className="flex items-center gap-2 py-2">
      <Icon className={cn("size-4 shrink-0", iconClass)} />
      <button
        type="button"
        className="cursor-pointer text-sm font-semibold hover:underline"
        onClick={() => onView(item.symbol)}
      >
        {item.symbol}
      </button>
      <div className="flex items-center gap-1 ml-auto">
        {item.breakout && (
          <Badge variant="default" className="text-xs">
            {t("common.signals.breakout")}
          </Badge>
        )}
        {item.rvol != null && (
          <Badge variant={item.rvol > 2 ? "destructive" : "outline"} className="text-xs">
            {t("common.signals.rvolBadge", { value: item.rvol.toFixed(1) })}
          </Badge>
        )}
      </div>
      <div className="w-[50px] text-right">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full", item.signal === "BUY" ? "bg-up" : item.signal === "SELL" ? "bg-down" : "bg-neutral")}
            style={{ width: `${item.confidence * 100}%` }}
          />
        </div>
      </div>
      <span className="w-[40px] text-right font-mono text-xs tabular-nums text-muted-foreground">
        {item.confidence != null ? `${(item.confidence * 100).toFixed(0)}%` : "—"}
      </span>
    </div>
  );
}

function RelativeTime({ timestamp }: { timestamp: string | null }) {
  const { t } = useTranslation();
  if (!timestamp) return <span className="text-xs text-muted-foreground">—</span>;

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return <span className="text-xs text-muted-foreground">{t("common.cache.expiresInSeconds", { count: 0 })}</span>;
  if (diffMins < 60) return <span className="text-xs text-muted-foreground">{t("common.cache.expiresInMinutes", { count: diffMins })}</span>;
  if (diffHours < 24) return <span className="text-xs text-muted-foreground">{diffHours}h ago</span>;
  return <span className="text-xs text-muted-foreground">{diffDays}d ago</span>;
}

export default function TopSignalsCard({ className }: TopSignalsCardProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState<TopSignalsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getTopSignals(10);
      setData(result);
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
          <div className="flex items-center justify-between">
            <div>
              <Skeleton className="h-4 w-32" />
              <Skeleton className="mt-1 h-3 w-24" />
            </div>
            <Skeleton className="h-6 w-6" />
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4 pt-0">
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className={className}>
        <CardHeader className="px-4 pb-3 pt-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">{t("dashboard.topSignals.title")}</div>
            </div>
            <Button variant="ghost" size="icon" className="size-6" onClick={fetchData}>
              <RefreshCw className="size-3" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4 pt-0">
          <p className="py-4 text-center text-sm text-muted-foreground">{t("signals.noSignalData")}</p>
        </CardContent>
      </Card>
    );
  }

  const hasData = (data.buys.length > 0 || data.sells.length > 0);

  if (!hasData) {
    return (
      <Card className={className}>
        <CardHeader className="px-4 pb-3 pt-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">{t("dashboard.topSignals.title")}</div>
            </div>
            <Button variant="ghost" size="icon" className="size-6" onClick={fetchData}>
              <RefreshCw className="size-3" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4 pt-0">
          <p className="py-4 text-center text-sm text-muted-foreground">{t("signals.empty.title")}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="px-4 pb-3 pt-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-1.5">
              <div className="text-sm font-medium">{t("dashboard.topSignals.title")}</div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info
                    className="size-3.5 cursor-help text-muted-foreground"
                    aria-label={t("dashboard.topSignals.hint")}
                  />
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-[280px] text-xs">
                  {t("dashboard.topSignals.hint")}
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="flex items-center gap-2">
              <p className="text-xs text-muted-foreground">
                {data.scanned_at ? `${t("dashboard.topSignals.lastScan")} ` : ""}
              </p>
              <RelativeTime timestamp={data.scanned_at} />
            </div>
          </div>
          <Button variant="ghost" size="icon" className="size-6" onClick={fetchData}>
            <RefreshCw className="size-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        <Tabs defaultValue="buys" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="buys" className="text-xs">
              {t("dashboard.topSignals.buys")} ({data.buys.length})
            </TabsTrigger>
            <TabsTrigger value="sells" className="text-xs">
              {t("dashboard.topSignals.sells")} ({data.sells.length})
            </TabsTrigger>
          </TabsList>
          <TabsContent value="buys" className="mt-2">
            {data.buys.length === 0 ? (
              <p className="py-2 text-center text-xs text-muted-foreground">{t("signals.empty.title")}</p>
            ) : (
              <div className="max-h-[200px] overflow-y-auto">
                {data.buys.map((item) => (
                  <SignalRow key={item.symbol} item={item} onView={handleView} />
                ))}
              </div>
            )}
          </TabsContent>
          <TabsContent value="sells" className="mt-2">
            {data.sells.length === 0 ? (
              <p className="py-2 text-center text-xs text-muted-foreground">{t("signals.empty.title")}</p>
            ) : (
              <div className="max-h-[200px] overflow-y-auto">
                {data.sells.map((item) => (
                  <SignalRow key={item.symbol} item={item} onView={handleView} />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}