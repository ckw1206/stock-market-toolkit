import { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowDown, ArrowUp, SlidersHorizontal } from "lucide-react";
import {
  getScreener,
  type ScreenerData,
  type ScreenerFilters,
  type ScreenerItem,
} from "@/api/stockApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

const SORTABLE: { key: string; labelKey: string }[] = [
  { key: "score", labelKey: "screener.columns.score" },
  { key: "price", labelKey: "screener.columns.price" },
  { key: "rsi", labelKey: "screener.columns.rsi" },
  { key: "rvol", labelKey: "screener.columns.rvol" },
  { key: "pct_from_52w_high", labelKey: "screener.columns.pctFrom52wHigh" },
  { key: "pct_change_1d", labelKey: "screener.columns.pctChange1d" },
];

const ALL = "__all__";

type Filters = {
  signal: string;
  rsiMin: string;
  rsiMax: string;
  rvolMin: string;
  breakout: boolean;
  aboveSma50: boolean;
  sector: string;
};

const DEFAULT_FILTERS: Filters = {
  signal: ALL,
  rsiMin: "",
  rsiMax: "",
  rvolMin: "",
  breakout: false,
  aboveSma50: false,
  sector: ALL,
};

function toQuery(f: Filters, sort: string, order: "asc" | "desc"): ScreenerFilters {
  return {
    signal: f.signal === ALL ? undefined : f.signal,
    rsi_min: f.rsiMin === "" ? undefined : Number(f.rsiMin),
    rsi_max: f.rsiMax === "" ? undefined : Number(f.rsiMax),
    rvol_min: f.rvolMin === "" ? undefined : Number(f.rvolMin),
    breakout: f.breakout ? true : undefined,
    above_sma50: f.aboveSma50 ? true : undefined,
    sector: f.sector === ALL ? undefined : f.sector,
    sort,
    order,
    limit: 100,
  };
}

function fmt(v: number | null | undefined, digits = 2): string {
  return v == null ? "—" : v.toFixed(digits);
}

function signed(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export default function ScreenerPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [sort, setSort] = useState("score");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [data, setData] = useState<ScreenerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sector options come from the current result set so the list always
  // reflects what the latest scan actually contains.
  const sectors = useMemo(() => {
    const s = new Set<string>();
    data?.results.forEach((r) => r.sector && s.add(r.sector));
    return Array.from(s).sort();
  }, [data]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        setData(await getScreener(toQuery(filters, sort, order)));
      } catch (err) {
        setError(err instanceof Error ? err.message : t("screener.loadFailed"));
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- t is stable
  }, [filters, sort, order]);

  const handleSort = (key: string) => {
    if (sort === key) {
      setOrder(order === "desc" ? "asc" : "desc");
    } else {
      setSort(key);
      setOrder("desc");
    }
  };

  const set = <K extends keyof Filters>(key: K, value: Filters[K]) =>
    setFilters((f) => ({ ...f, [key]: value }));

  return (
    <div className="container mx-auto space-y-4 p-4">
      <div className="flex items-center gap-2">
        <SlidersHorizontal className="size-5" />
        <h1 className="text-xl font-semibold">{t("screener.title")}</h1>
        {data?.scanned_at && (
          <span className="ml-auto text-xs text-muted-foreground">
            {t("screener.scannedAt", {
              time: new Date(data.scanned_at).toLocaleString(),
            })}
          </span>
        )}
      </div>

      <Card>
        <CardHeader className="px-4 pb-0 pt-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-7">
            <div className="space-y-1">
              <Label className="text-xs">{t("screener.filters.signal")}</Label>
              <Select value={filters.signal} onValueChange={(v) => set("signal", v)}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>{t("screener.filters.any")}</SelectItem>
                  <SelectItem value="BUY">BUY</SelectItem>
                  <SelectItem value="SELL">SELL</SelectItem>
                  <SelectItem value="NEUTRAL">NEUTRAL</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">{t("screener.filters.rsiMin")}</Label>
              <Input
                className="h-8 text-xs"
                type="number"
                min={0}
                max={100}
                value={filters.rsiMin}
                onChange={(e) => set("rsiMin", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">{t("screener.filters.rsiMax")}</Label>
              <Input
                className="h-8 text-xs"
                type="number"
                min={0}
                max={100}
                value={filters.rsiMax}
                onChange={(e) => set("rsiMax", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">{t("screener.filters.rvolMin")}</Label>
              <Input
                className="h-8 text-xs"
                type="number"
                min={0}
                step={0.1}
                value={filters.rvolMin}
                onChange={(e) => set("rvolMin", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">{t("screener.filters.sector")}</Label>
              <Select value={filters.sector} onValueChange={(v) => set("sector", v)}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>{t("screener.filters.any")}</SelectItem>
                  {sectors.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-2 pb-1">
              <Switch
                id="breakout"
                checked={filters.breakout}
                onCheckedChange={(v) => set("breakout", v)}
              />
              <Label htmlFor="breakout" className="text-xs">
                {t("screener.filters.breakout")}
              </Label>
            </div>
            <div className="flex items-end gap-2 pb-1">
              <Switch
                id="aboveSma50"
                checked={filters.aboveSma50}
                onCheckedChange={(v) => set("aboveSma50", v)}
              />
              <Label htmlFor="aboveSma50" className="text-xs">
                {t("screener.filters.aboveSma50")}
              </Label>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-4">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : error ? (
            <p className="py-8 text-center text-sm text-muted-foreground">{error}</p>
          ) : !data || data.results.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {data?.scanned_at ? t("screener.noMatches") : t("screener.noScanYet")}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                    <th className="py-2 pr-2">{t("screener.columns.symbol")}</th>
                    <th className="py-2 pr-2">{t("screener.columns.signal")}</th>
                    {SORTABLE.map((c) => (
                      <th key={c.key} className="py-2 pr-2">
                        <button
                          type="button"
                          className="inline-flex cursor-pointer items-center gap-1 uppercase hover:text-foreground"
                          onClick={() => handleSort(c.key)}
                        >
                          {t(c.labelKey)}
                          {sort === c.key &&
                            (order === "desc" ? (
                              <ArrowDown className="size-3" />
                            ) : (
                              <ArrowUp className="size-3" />
                            ))}
                        </button>
                      </th>
                    ))}
                    <th className="py-2">{t("screener.columns.sector")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((r: ScreenerItem) => (
                    <tr
                      key={r.symbol}
                      className="cursor-pointer border-b last:border-0 hover:bg-muted/50"
                      onClick={() => navigate(`/?symbol=${r.symbol}`)}
                    >
                      <td className="py-2 pr-2 font-semibold">
                        {r.symbol}
                        {r.breakout && (
                          <Badge variant="default" className="ml-1.5 text-[10px]">
                            {t("common.signals.breakout")}
                          </Badge>
                        )}
                      </td>
                      <td className="py-2 pr-2">
                        <Badge
                          variant={
                            r.signal === "BUY"
                              ? "default"
                              : r.signal === "SELL"
                                ? "destructive"
                                : "secondary"
                          }
                          className="text-[10px]"
                        >
                          {r.signal}
                        </Badge>
                      </td>
                      <td className="py-2 pr-2 font-mono tabular-nums">{fmt(r.score)}</td>
                      <td className="py-2 pr-2 font-mono tabular-nums">${fmt(r.price)}</td>
                      <td className="py-2 pr-2 font-mono tabular-nums">{fmt(r.rsi, 0)}</td>
                      <td className="py-2 pr-2 font-mono tabular-nums">
                        {r.rvol != null ? `${r.rvol.toFixed(1)}x` : "—"}
                      </td>
                      <td className="py-2 pr-2 font-mono tabular-nums">
                        {signed(r.pct_from_52w_high)}
                      </td>
                      <td
                        className={cn(
                          "py-2 pr-2 font-mono tabular-nums",
                          r.pct_change_1d != null && r.pct_change_1d > 0 && "text-up",
                          r.pct_change_1d != null && r.pct_change_1d < 0 && "text-down",
                        )}
                      >
                        {signed(r.pct_change_1d)}
                      </td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {r.sector ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-2 flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  {t("screener.resultCount", { count: data.count })}
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setFilters(DEFAULT_FILTERS)}
                >
                  {t("screener.clearFilters")}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
