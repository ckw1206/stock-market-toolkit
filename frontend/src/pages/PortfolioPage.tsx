import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Wallet, TrendingUp, TrendingDown, X, RotateCcw } from "lucide-react";
import {
  getPaperPortfolio,
  getPaperHistory,
  postPaperTrade,
  deletePaperTrade,
  resetPaperPortfolio,
  type PaperPortfolioData,
  type PaperTradeRecord,
} from "@/api/stockApi";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import SymbolSearch from "@/components/common/SymbolSearch";
import { toast } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

function fmtMoney(v: number | null | undefined): string {
  return v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtSigned(v: number | null | undefined, digits = 2): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

export default function PortfolioPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [portfolio, setPortfolio] = useState<PaperPortfolioData | null>(null);
  const [history, setHistory] = useState<PaperTradeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [symbol, setSymbol] = useState(() => searchParams.get("symbol")?.toUpperCase() || "AAPL");
  const [side, setSide] = useState<"buy" | "sell">(
    () => (searchParams.get("side") === "sell" ? "sell" : "buy"),
  );
  const [qty, setQty] = useState("1");
  const [executedAt, setExecutedAt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [undoingId, setUndoingId] = useState<number | null>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetCash, setResetCash] = useState("");
  const [resetting, setResetting] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [p, h] = await Promise.all([getPaperPortfolio(), getPaperHistory()]);
      setPortfolio(p);
      setHistory(h.trades);
    } catch {
      toast.error(t("portfolio.errors.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- non-critical state update for data fetch
    refresh();
  }, [refresh]);

  const submitTrade = async () => {
    const qtyNum = Number(qty);
    if (!symbol || !qtyNum || qtyNum <= 0) {
      toast.error(t("portfolio.errors.invalidTrade"));
      return;
    }
    setSubmitting(true);
    try {
      const iso = executedAt ? new Date(executedAt).toISOString() : undefined;
      const result = await postPaperTrade(symbol, side, qtyNum, iso);
      toast.success(
        t(side === "buy" ? "portfolio.toast.bought" : "portfolio.toast.sold", {
          qty: result.qty,
          symbol: result.symbol,
          price: result.price.toFixed(2),
        })
      );
      setExecutedAt("");
      await refresh();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || t("portfolio.errors.tradeFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const undoTrade = async (id: number) => {
    setUndoingId(id);
    try {
      await deletePaperTrade(id);
      toast.success(t("portfolio.toast.undone"));
      await refresh();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || t("portfolio.errors.undoFailed"));
    } finally {
      setUndoingId(null);
    }
  };

  const submitReset = async () => {
    const cashNum = Number(resetCash);
    setResetting(true);
    try {
      await resetPaperPortfolio(resetCash && cashNum > 0 ? cashNum : undefined);
      toast.success(t("portfolio.toast.reset"));
      setResetOpen(false);
      setResetCash("");
      await refresh();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || t("portfolio.errors.resetFailed"));
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="container mx-auto space-y-4 p-4">
      <div className="flex items-center gap-2">
        <Wallet className="size-5" />
        <h1 className="text-xl font-semibold">{t("portfolio.title")}</h1>
        <Button
          variant="outline"
          size="sm"
          className="ml-auto"
          onClick={() => {
            setResetCash(portfolio ? String(portfolio.starting_cash) : "");
            setResetOpen(true);
          }}
        >
          <RotateCcw className="mr-1 size-3" />
          {t("portfolio.reset.button")}
        </Button>
      </div>

      {loading && !portfolio ? (
        <div className="space-y-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <p className="text-xs uppercase text-muted-foreground">{t("portfolio.cash")}</p>
                <p className="font-mono text-lg font-semibold tabular-nums">${fmtMoney(portfolio?.cash)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs uppercase text-muted-foreground">{t("portfolio.equity")}</p>
                <p className="font-mono text-lg font-semibold tabular-nums">${fmtMoney(portfolio?.equity)}</p>
              </CardContent>
            </Card>
            <Card className="col-span-2 sm:col-span-2">
              <CardContent className="p-4">
                <p className="text-xs uppercase text-muted-foreground">{t("portfolio.unrealizedPnl")}</p>
                <p
                  className={cn(
                    "font-mono text-lg font-semibold tabular-nums",
                    (portfolio?.total_unrealized_pnl ?? 0) > 0 && "text-up",
                    (portfolio?.total_unrealized_pnl ?? 0) < 0 && "text-down",
                  )}
                >
                  ${fmtSigned(portfolio?.total_unrealized_pnl)}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="px-4 pb-0 pt-4">
              <CardTitle className="text-sm">{t("portfolio.trade.title")}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-end gap-3 p-4">
              <div className="space-y-1">
                <Label className="text-xs">{t("portfolio.trade.symbol")}</Label>
                <SymbolSearch value={symbol} onSearch={setSymbol} loading={submitting} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t("portfolio.trade.side")}</Label>
                <Select value={side} onValueChange={(v) => setSide(v as "buy" | "sell")}>
                  <SelectTrigger className="h-9 w-28 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="buy">{t("portfolio.trade.buy")}</SelectItem>
                    <SelectItem value="sell">{t("portfolio.trade.sell")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t("portfolio.trade.qty")}</Label>
                <Input
                  type="number"
                  min={0.0001}
                  step={1}
                  value={qty}
                  onChange={(e) => setQty(e.target.value)}
                  className="h-9 w-24 text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t("portfolio.trade.executedAt")}</Label>
                <Input
                  type="datetime-local"
                  value={executedAt}
                  max={new Date().toISOString().slice(0, 16)}
                  onChange={(e) => setExecutedAt(e.target.value)}
                  className="h-9 w-48 text-xs"
                />
              </div>
              <Button size="sm" onClick={submitTrade} disabled={submitting}>
                {t(side === "buy" ? "portfolio.trade.buy" : "portfolio.trade.sell")}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="px-4 pb-0 pt-4">
              <CardTitle className="text-sm">{t("portfolio.positions.title")}</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {!portfolio || portfolio.positions.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">{t("portfolio.positions.empty")}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                        <th className="py-2 pr-2">{t("portfolio.positions.symbol")}</th>
                        <th className="py-2 pr-2">{t("portfolio.positions.qty")}</th>
                        <th className="py-2 pr-2">{t("portfolio.positions.avgCost")}</th>
                        <th className="py-2 pr-2">{t("portfolio.positions.lastPrice")}</th>
                        <th className="py-2 pr-2">{t("portfolio.positions.marketValue")}</th>
                        <th className="py-2">{t("portfolio.positions.unrealizedPnl")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.positions.map((p) => (
                        <tr key={p.symbol} className="border-b last:border-0">
                          <td className="py-2 pr-2 font-semibold">{p.symbol}</td>
                          <td className="py-2 pr-2 font-mono tabular-nums">{p.qty}</td>
                          <td className="py-2 pr-2 font-mono tabular-nums">${fmtMoney(p.avg_cost)}</td>
                          <td className="py-2 pr-2 font-mono tabular-nums">${fmtMoney(p.last_price)}</td>
                          <td className="py-2 pr-2 font-mono tabular-nums">${fmtMoney(p.market_value)}</td>
                          <td
                            className={cn(
                              "py-2 font-mono tabular-nums",
                              (p.unrealized_pnl ?? 0) > 0 && "text-up",
                              (p.unrealized_pnl ?? 0) < 0 && "text-down",
                            )}
                          >
                            {p.unrealized_pnl != null && (p.unrealized_pnl >= 0 ? <TrendingUp className="mr-1 inline size-3" /> : <TrendingDown className="mr-1 inline size-3" />)}
                            ${fmtSigned(p.unrealized_pnl)}
                            {p.unrealized_pnl_pct != null && ` (${fmtSigned(p.unrealized_pnl_pct, 1)}%)`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="px-4 pb-0 pt-4">
              <CardTitle className="text-sm">{t("portfolio.history.title")}</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {history.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">{t("portfolio.history.empty")}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                        <th className="py-2 pr-2">{t("portfolio.positions.symbol")}</th>
                        <th className="py-2 pr-2">{t("portfolio.trade.side")}</th>
                        <th className="py-2 pr-2">{t("portfolio.positions.qty")}</th>
                        <th className="py-2 pr-2">{t("common.fields.price")}</th>
                        <th className="py-2 pr-2">{t("portfolio.history.executedAt")}</th>
                        <th className="py-2 text-right">{t("portfolio.history.actions")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((tr) => (
                        <tr key={tr.id} className="border-b last:border-0">
                          <td className="py-2 pr-2 font-semibold">{tr.symbol}</td>
                          <td className="py-2 pr-2">
                            <Badge variant={tr.side === "buy" ? "default" : "destructive"} className="text-[10px]">
                              {t(tr.side === "buy" ? "portfolio.trade.buy" : "portfolio.trade.sell")}
                            </Badge>
                          </td>
                          <td className="py-2 pr-2 font-mono tabular-nums">{tr.qty}</td>
                          <td className="py-2 pr-2 font-mono tabular-nums">${fmtMoney(tr.price)}</td>
                          <td className="py-2 pr-2 text-xs text-muted-foreground">
                            {tr.executed_at ? new Date(tr.executed_at).toLocaleString() : "—"}
                          </td>
                          <td className="py-2 text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs"
                              onClick={() => undoTrade(tr.id)}
                              disabled={undoingId === tr.id}
                              title={t("portfolio.history.undo")}
                            >
                              <X className="size-3" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <Dialog open={resetOpen} onOpenChange={setResetOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("portfolio.reset.title")}</DialogTitle>
            <DialogDescription>{t("portfolio.reset.description")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-1">
            <Label className="text-xs">{t("portfolio.reset.startingCashLabel")}</Label>
            <Input
              type="number"
              min={1}
              step={1000}
              value={resetCash}
              onChange={(e) => setResetCash(e.target.value)}
              className="h-9 text-sm"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetOpen(false)} disabled={resetting}>
              {t("portfolio.reset.cancel")}
            </Button>
            <Button variant="destructive" onClick={submitReset} disabled={resetting}>
              {t("portfolio.reset.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
