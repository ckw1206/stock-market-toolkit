import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  Badge, Button, Card, CardContent, CardHeader, CardTitle,
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
  Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Skeleton,
} from "@/components/ui";
import {
  acceptSuggestion, createHoldingsTxn, deleteHoldingsTxn, dismissSuggestion,
  getHoldingsSuggestions, getHoldingsSummary, listHoldingsTxns,
  updateHoldingsTxn,
  type HoldingsSummary, type HoldingsTxn, type Suggestion, type TxnPayload,
} from "@/api/holdingsApi";
import {
  deriveCurrency, fieldsForType, validateTransaction,
  type AdjustVariant, type Currency, type TxnFormInput, type TxnType,
} from "@/lib/holdings";
import { fmt } from "@/lib/format";

const TYPES: TxnType[] = [
  "buy", "sell", "dividend", "deposit", "withdrawal", "split", "adjust",
];

const num = (s: string | null | undefined): number | null =>
  s == null || s === "" ? null : Number(s);

const emptyForm = (): TxnFormInput & { note: string } => ({
  type: "buy", adjustVariant: "position",
  tradeDate: new Date().toISOString().slice(0, 10),
  symbol: "", qty: "", price: "", amount: "", fee: "0",
  currency: "USD", note: "",
});

export default function HoldingsPage() {
  const { t } = useTranslation();
  const [summary, setSummary] = useState<HoldingsSummary | null>(null);
  const [txns, setTxns] = useState<HoldingsTxn[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [degradedSymbols, setDegradedSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [showWarnings, setShowWarnings] = useState(true);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [acceptAmounts, setAcceptAmounts] = useState<Record<string, string>>({});
  const [filterSymbol, setFilterSymbol] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [currencyTouched, setCurrencyTouched] = useState(false);
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [s, list, sug] = await Promise.all([
        getHoldingsSummary(), listHoldingsTxns(), getHoldingsSuggestions(),
      ]);
      setSummary(s);
      setTxns(list);
      setSuggestions(sug.suggestions);
      setDegradedSymbols(sug.degraded_symbols);
      setShowWarnings(true);
    } catch {
      toast.error(t("holdings.toast.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { refresh(); }, []);

  const flaggedIds = useMemo(
    () => new Set((summary?.warnings ?? []).map((w) => w.transaction_id)),
    [summary],
  );

  const visibleTxns = useMemo(() => txns.filter((x) =>
    (!filterSymbol || (x.symbol ?? "").includes(filterSymbol.trim().toUpperCase())) &&
    (filterType === "all" || x.type === filterType)), [txns, filterSymbol, filterType]);

  const setField = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));

  const onSymbolChange = (symbol: string) => {
    setField({ symbol });
    if (!currencyTouched && symbol.trim()) {
      setField({ symbol, currency: deriveCurrency(symbol) });
    }
  };

  const openAdd = () => {
    setEditingId(null);
    setForm(emptyForm());
    setCurrencyTouched(false);
    setFormOpen(true);
  };

  const openEdit = (txn: HoldingsTxn) => {
    setEditingId(txn.id);
    setForm({
      type: txn.type,
      adjustVariant: txn.type === "adjust" && txn.symbol == null ? "cash" : "position",
      tradeDate: txn.trade_date,
      symbol: txn.symbol ?? "", qty: txn.qty ?? "", price: txn.price ?? "",
      amount: txn.amount ?? "", fee: txn.fee, currency: txn.currency,
      note: txn.note ?? "",
    });
    setCurrencyTouched(true);
    setFormOpen(true);
  };

  const submitForm = async () => {
    const error = validateTransaction(form);
    if (error) { toast.error(t(error)); return; }
    const fields = fieldsForType(form.type, form.adjustVariant);
    const payload: TxnPayload = {
      type: form.type,
      trade_date: form.tradeDate,
      symbol: fields.has("symbol") ? form.symbol.trim().toUpperCase() : null,
      qty: fields.has("qty") ? form.qty : null,
      price: fields.has("price") ? form.price : null,
      amount: fields.has("amount") ? form.amount : null,
      fee: fields.has("fee") && form.fee !== "" ? form.fee : "0",
      currency: form.currency,
      note: form.note || null,
    };
    setSaving(true);
    try {
      if (editingId == null) await createHoldingsTxn(payload);
      else await updateHoldingsTxn(editingId, payload);
      toast.success(t("holdings.toast.saved"));
      setFormOpen(false);
      await refresh();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : t("holdings.toast.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const removeTxn = async (id: number) => {
    try {
      await deleteHoldingsTxn(id);
      toast.success(t("holdings.toast.deleted"));
      await refresh();
    } catch {
      toast.error(t("holdings.toast.saveFailed"));
    }
  };

  const sugKey = (s: Suggestion) => `${s.symbol}|${s.type}|${s.ex_date}`;

  const onAccept = async (s: Suggestion) => {
    try {
      await acceptSuggestion({
        symbol: s.symbol, type: s.type, ex_date: s.ex_date,
        ...(s.type === "dividend"
          ? { amount: acceptAmounts[sugKey(s)] || s.gross_amount || "0" }
          : { ratio: s.ratio ?? "1" }),
      });
      toast.success(t("holdings.toast.accepted"));
      await refresh();
    } catch {
      toast.error(t("holdings.toast.saveFailed"));
    }
  };

  const onDismiss = async (s: Suggestion) => {
    try {
      await dismissSuggestion({ symbol: s.symbol, type: s.type, ex_date: s.ex_date });
      toast.success(t("holdings.toast.dismissed"));
      await refresh();
    } catch {
      toast.error(t("holdings.toast.saveFailed"));
    }
  };

  const fields = fieldsForType(form.type, form.adjustVariant);

  if (loading && !summary) {
    return (
      <div className="space-y-2 p-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-2xl font-semibold">{t("holdings.title")}</h1>

      <div className="grid gap-3 md:grid-cols-2">
        {Object.entries(summary?.currencies ?? {}).map(([cur, c]) => (
          <Card key={cur}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Badge>{cur}</Badge>
                {!c.market_value_complete && (
                  <span className="text-xs text-muted-foreground">
                    {t("holdings.incomplete")}
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
              <div>
                <div className="text-xs text-muted-foreground">{t("holdings.cash")}</div>
                <div>{fmt(num(c.cash))}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">{t("holdings.marketValue")}</div>
                <div>{fmt(num(c.market_value))}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">{t("holdings.unrealizedPnl")}</div>
                <div>{fmt(num(c.unrealized_pnl))}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">
                  {t("holdings.realizedPnl")} + {t("holdings.dividends")}
                </div>
                <div>{fmt((num(c.realized_pnl) ?? 0) + (num(c.dividends) ?? 0))}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {showWarnings && (summary?.warnings.length ?? 0) > 0 && (
        <div className="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-medium">{t("holdings.warnings.title")}</span>
            <Button variant="ghost" size="sm" onClick={() => setShowWarnings(false)}>
              {t("holdings.warnings.hide")}
            </Button>
          </div>
          <ul className="list-disc pl-5">
            {summary!.warnings.map((w, i) => (
              <li key={i}>{w.trade_date}: {w.message}</li>
            ))}
          </ul>
        </div>
      )}

      {suggestions.length > 0 && (
        <div className="flex items-center justify-between rounded-md border p-3 text-sm">
          <span>{t("holdings.suggestions.banner", { count: suggestions.length })}</span>
          <Button size="sm" onClick={() => setReviewOpen(true)}>
            {t("holdings.suggestions.review")}
          </Button>
        </div>
      )}
      {degradedSymbols.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {t("holdings.suggestions.degraded", { symbols: degradedSymbols.join(", ") })}
        </p>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("holdings.holdingsTable.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          {(summary?.holdings.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">{t("holdings.holdingsTable.empty")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                    <th className="py-2 pr-2">{t("holdings.holdingsTable.symbol")}</th>
                    <th className="py-2 pr-2">{t("holdings.holdingsTable.qty")}</th>
                    <th className="py-2 pr-2">{t("holdings.holdingsTable.avgCost")}</th>
                    <th className="py-2 pr-2">{t("holdings.holdingsTable.price")}</th>
                    <th className="py-2 pr-2">{t("holdings.holdingsTable.marketValue")}</th>
                    <th className="py-2 pr-2">{t("holdings.holdingsTable.unrealizedPnl")}</th>
                    <th className="py-2 pr-2">{t("holdings.holdingsTable.realizedPnl")}</th>
                    <th className="py-2 pr-2">{t("holdings.holdingsTable.dividends")}</th>
                  </tr>
                </thead>
                <tbody>
                  {summary!.holdings.map((h) => {
                    const mv = num(h.market_value);
                    const cost = (num(h.avg_cost) ?? 0) * (num(h.qty) ?? 0);
                    const upnlPct = mv != null && cost > 0
                      ? ((mv - cost) / cost) * 100 : null;
                    return (
                      <tr key={h.symbol} className="border-b last:border-0">
                        <td className="py-2 pr-2">
                          {h.symbol} <Badge className="ml-1">{h.currency}</Badge>
                        </td>
                        <td className="py-2 pr-2">{fmt(num(h.qty))}</td>
                        <td className="py-2 pr-2">{fmt(num(h.avg_cost))}</td>
                        <td className="py-2 pr-2">{fmt(num(h.price))}</td>
                        <td className="py-2 pr-2">{fmt(mv)}</td>
                        <td className="py-2 pr-2">
                          {fmt(num(h.unrealized_pnl))}
                          {upnlPct != null && ` (${upnlPct >= 0 ? "+" : ""}${upnlPct.toFixed(2)}%)`}
                        </td>
                        <td className="py-2 pr-2">{fmt(num(h.realized_pnl))}</td>
                        <td className="py-2 pr-2">{fmt(num(h.dividends))}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-base">{t("holdings.txns.title")}</CardTitle>
          <div className="flex items-center gap-2">
            <Input
              placeholder={t("holdings.txns.filterSymbol")}
              value={filterSymbol}
              onChange={(e) => setFilterSymbol(e.target.value)}
              className="h-8 w-40 text-sm"
            />
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="h-8 w-36 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t("holdings.txns.filterType")}</SelectItem>
                {TYPES.map((ty) => (
                  <SelectItem key={ty} value={ty}>{t(`holdings.form.types.${ty}`)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button size="sm" onClick={openAdd}>{t("holdings.txns.add")}</Button>
          </div>
        </CardHeader>
        <CardContent>
          {visibleTxns.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("holdings.txns.empty")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase text-muted-foreground">
                    <th className="py-2 pr-2">{t("holdings.txns.date")}</th>
                    <th className="py-2 pr-2">{t("holdings.txns.type")}</th>
                    <th className="py-2 pr-2">{t("holdings.txns.symbol")}</th>
                    <th className="py-2 pr-2">{t("holdings.txns.qty")}</th>
                    <th className="py-2 pr-2">{t("holdings.txns.price")}</th>
                    <th className="py-2 pr-2">{t("holdings.txns.amount")}</th>
                    <th className="py-2 pr-2">{t("holdings.txns.fee")}</th>
                    <th className="py-2 pr-2">{t("holdings.txns.currency")}</th>
                    <th className="py-2 pr-2" />
                  </tr>
                </thead>
                <tbody>
                  {visibleTxns.map((x) => (
                    <tr key={x.id} className="border-b last:border-0">
                      <td className="py-2 pr-2">
                        {x.trade_date}
                        {flaggedIds.has(x.id) && (
                          <span title={t("holdings.txns.flagged")} className="ml-1 text-amber-500">!</span>
                        )}
                      </td>
                      <td className="py-2 pr-2">{t(`holdings.form.types.${x.type}`)}</td>
                      <td className="py-2 pr-2">{x.symbol ?? "—"}</td>
                      <td className="py-2 pr-2">{x.qty ?? "—"}</td>
                      <td className="py-2 pr-2">{x.price ?? "—"}</td>
                      <td className="py-2 pr-2">{x.amount ?? "—"}</td>
                      <td className="py-2 pr-2">{x.fee}</td>
                      <td className="py-2 pr-2">{x.currency}</td>
                      <td className="py-2 pr-2 text-right">
                        <Button variant="ghost" size="sm" onClick={() => openEdit(x)}>
                          {t("holdings.txns.edit")}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => removeTxn(x.id)}>
                          {t("holdings.txns.delete")}
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

      <Dialog open={reviewOpen} onOpenChange={setReviewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("holdings.suggestions.title")}</DialogTitle>
          </DialogHeader>
          {suggestions.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("holdings.suggestions.empty")}</p>
          ) : (
            <div className="max-h-80 space-y-3 overflow-y-auto">
              {suggestions.map((s) => (
                <div key={sugKey(s)} className="rounded-md border p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {s.symbol} · {t(`holdings.suggestions.${s.type}`)} · {s.ex_date}
                    </span>
                    <Badge>{s.currency}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {t("holdings.suggestions.sharesHeld", { shares: s.shares, date: s.ex_date })}
                    {s.type === "split" && ` · ×${s.ratio}`}
                  </div>
                  {s.type === "dividend" && (
                    <div className="mt-2 space-y-1">
                      <Label className="text-xs">{t("holdings.suggestions.amountLabel")}</Label>
                      <Input
                        type="number"
                        className="h-8 text-sm"
                        value={acceptAmounts[sugKey(s)] ?? s.gross_amount ?? ""}
                        onChange={(e) => setAcceptAmounts((m) => ({
                          ...m, [sugKey(s)]: e.target.value,
                        }))}
                      />
                    </div>
                  )}
                  <div className="mt-2 flex gap-2">
                    <Button size="sm" onClick={() => onAccept(s)}>
                      {t("holdings.suggestions.accept")}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => onDismiss(s)}>
                      {t("holdings.suggestions.dismiss")}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingId == null ? t("holdings.form.addTitle") : t("holdings.form.editTitle")}
            </DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">{t("holdings.form.type")}</Label>
              <Select value={form.type} onValueChange={(v) => setField({ type: v as TxnType })}>
                <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TYPES.map((ty) => (
                    <SelectItem key={ty} value={ty}>{t(`holdings.form.types.${ty}`)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {form.type === "adjust" && (
              <div className="space-y-1">
                <Label className="text-xs">{t("holdings.form.adjustVariant")}</Label>
                <Select
                  value={form.adjustVariant}
                  onValueChange={(v) => setField({ adjustVariant: v as AdjustVariant })}
                >
                  <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="position">{t("holdings.form.adjustPosition")}</SelectItem>
                    <SelectItem value="cash">{t("holdings.form.adjustCash")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-1">
              <Label className="text-xs">{t("holdings.form.date")}</Label>
              <Input type="date" value={form.tradeDate} className="h-9 text-sm"
                     onChange={(e) => setField({ tradeDate: e.target.value })} />
            </div>
            {fields.has("symbol") && (
              <div className="space-y-1">
                <Label className="text-xs">{t("holdings.form.symbol")}</Label>
                <Input value={form.symbol} className="h-9 text-sm"
                       onChange={(e) => onSymbolChange(e.target.value)} />
              </div>
            )}
            {fields.has("qty") && (
              <div className="space-y-1">
                <Label className="text-xs">
                  {form.type === "split" ? t("holdings.form.ratio") : t("holdings.form.qty")}
                </Label>
                <Input type="number" value={form.qty} className="h-9 text-sm"
                       onChange={(e) => setField({ qty: e.target.value })} />
              </div>
            )}
            {fields.has("price") && (
              <div className="space-y-1">
                <Label className="text-xs">
                  {form.type === "adjust" ? t("holdings.form.avgCost") : t("holdings.form.price")}
                </Label>
                <Input type="number" value={form.price} className="h-9 text-sm"
                       onChange={(e) => setField({ price: e.target.value })} />
              </div>
            )}
            {fields.has("amount") && (
              <div className="space-y-1">
                <Label className="text-xs">{t("holdings.form.amount")}</Label>
                <Input type="number" value={form.amount} className="h-9 text-sm"
                       onChange={(e) => setField({ amount: e.target.value })} />
              </div>
            )}
            {fields.has("fee") && (
              <div className="space-y-1">
                <Label className="text-xs">{t("holdings.form.fee")}</Label>
                <Input type="number" value={form.fee} className="h-9 text-sm"
                       onChange={(e) => setField({ fee: e.target.value })} />
              </div>
            )}
            <div className="space-y-1">
              <Label className="text-xs">{t("holdings.form.currency")}</Label>
              <Select
                value={form.currency}
                onValueChange={(v) => { setCurrencyTouched(true); setField({ currency: v as Currency }); }}
              >
                <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="USD">USD</SelectItem>
                  <SelectItem value="TWD">TWD</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="col-span-2 space-y-1">
              <Label className="text-xs">{t("holdings.form.note")}</Label>
              <Input value={form.note} className="h-9 text-sm"
                     onChange={(e) => setField({ note: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormOpen(false)} disabled={saving}>
              {t("holdings.form.cancel")}
            </Button>
            <Button onClick={submitForm} disabled={saving}>
              {t("holdings.form.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}