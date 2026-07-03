import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  createAlert,
  getAlerts,
  updateAlert,
  deleteAlert,
  getTriggeredAlerts,
  markTriggeredAlertRead,
  getNotificationSettings,
  updateNotificationSettings,
  testDiscordWebhook,
  testSmtpSettings,
  type Alert,
  type TriggeredAlert,
  type NotificationSettings,
} from "../api/alertsApi";
import { getStockInfo } from "../api/stockApi";
import { getMarketStatus } from "../lib/marketHours";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
import { Skeleton } from "../components/ui/skeleton";
import { Bell, CheckCircle2, X, Plus, Trash2, Pencil } from "lucide-react";
import SymbolSearch from "@/components/common/SymbolSearch";
import { fmt } from "../lib/format";
import { toast } from "@/components/ui/sonner";

import type { TFunction } from "i18next";

// Enum VALUES sent to backend are stable; only the visible labels are translated.
const CONDITION_VALUES = ["above", "below", "pct_change_up", "pct_change_down"] as const;
const PERIOD_VALUES = ["5m", "15m", "30m", "1h", "4h", "1d"] as const;
const METRIC_VALUES = ["price", "rsi", "macd_hist", "signal", "pct_change"] as const;
const OPERATOR_VALUES = ["gt", "lt", "crosses_above", "eq"] as const;

function conditionLabel(t: TFunction, ct: string): string {
  return CONDITION_VALUES.includes(ct as typeof CONDITION_VALUES[number])
    ? t(`alerts.conditionTypes.${ct}`)
    : ct;
}

function metricLabel(t: TFunction, m: string): string {
  return METRIC_VALUES.includes(m as typeof METRIC_VALUES[number])
    ? t(`alerts.metrics.${m}`)
    : m;
}

function operatorLabel(t: TFunction, o: string): string {
  return OPERATOR_VALUES.includes(o as typeof OPERATOR_VALUES[number])
    ? t(`alerts.operators.${o}`)
    : o;
}

// Local form type for conditions: value stored as a string so the field can be empty
type ConditionFormItem = {
  metric: "price" | "rsi" | "macd_hist" | "signal" | "pct_change";
  operator: "gt" | "lt" | "crosses_above" | "eq";
  value: string;
};

/* ─── Create Alert Dialog ─── */
function CreateAlertDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (alert: Alert) => void;
}) {
  const { t } = useTranslation();
  const [symbol, setSymbol] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [symbolName, setSymbolName] = useState("");
  const [combinator, setCombinator] = useState<"all" | "any">("all");
  const [conditions, setConditions] = useState<ConditionFormItem[]>([
    { metric: "price", operator: "gt", value: "" },
  ]);
  const [period, setPeriod] = useState("1h");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);

  // Fetch current price when a symbol is selected
  useEffect(() => {
    if (!selectedSymbol) {
      setCurrentPrice(null); // eslint-disable-line react-hooks/set-state-in-effect
      return;
    }
    let cancelled = false;
    getStockInfo(selectedSymbol)
      .then(info => { if (!cancelled) setCurrentPrice(info.price || null); })
      .catch(() => { if (!cancelled) setCurrentPrice(null); });
    return () => { cancelled = true; };
  }, [selectedSymbol]);

  const updateCondition = (idx: number, field: string, value: string) => {
    setConditions(prev => prev.map((c, i) => i === idx ? { ...c, [field]: value } : c));
  };

  const addCondition = () => {
    setConditions(prev => [...prev, { metric: "price", operator: "gt", value: "" }]);
  };

  const removeCondition = (idx: number) => {
    setConditions(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim()) { setError(t("alerts.errors.symbolRequired")); return; }

    // Validate conditions: value must be a non-empty, parseable number
    for (const c of conditions) {
      if (c.value.trim() === "" || isNaN(Number(c.value))) {
        setError(t("alerts.errors.invalidConditionValue"));
        return;
      }
    }
    if (conditions.length === 0) { setError(t("alerts.errors.atLeastOneCondition")); return; }

    setLoading(true);
    setError("");
    try {
      const alert = await createAlert({
        symbol: symbol.trim().toUpperCase(),
        symbol_name: symbolName || undefined,
        period,
        combinator,
        conditions: conditions.map(c => ({ ...c, value: Number(c.value) })),
      });
      onCreated(alert);
      onClose();
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("alerts.errors.createFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={o => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("alerts.dialog.title")}</DialogTitle>
          <DialogDescription>
            {t("alerts.dialog.description")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="symbol">{t("alerts.dialog.symbol")}</Label>
              <SymbolSearch
                value={selectedSymbol}
                onSearch={(sym) => {
                  setSelectedSymbol(sym);
                  setSymbol(sym);
                }}
                onSelect={(result) => setSymbolName(result.name)}
              />
            </div>

            <div className="grid gap-2">
              <Label>{t("alerts.dialog.combinator")}</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={combinator === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCombinator("all")}
                >
                  {t("alerts.dialog.combinatorAll")}
                </Button>
                <Button
                  type="button"
                  variant={combinator === "any" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCombinator("any")}
                >
                  {t("alerts.dialog.combinatorAny")}
                </Button>
              </div>
            </div>

            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <Label>{t("alerts.dialog.conditions")}</Label>
                <Button type="button" variant="outline" size="sm" onClick={addCondition}>
                  <Plus className="size-3.5 mr-1" /> {t("alerts.conditions.add")}
                </Button>
              </div>
              {conditions.map((c, idx) => (
                <div key={idx} className="flex items-end gap-2">
                  <div className="flex-1">
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                      value={c.metric}
                      onChange={e => updateCondition(idx, "metric", e.target.value)}
                    >
                      {METRIC_VALUES.map(v => (
                        <option className="bg-background text-foreground" key={v} value={v}>{t(`alerts.metrics.${v}`)}</option>
                      ))}
                    </select>
                  </div>
                  <div className="w-28">
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                      value={c.operator}
                      onChange={e => updateCondition(idx, "operator", e.target.value)}
                    >
                      {OPERATOR_VALUES.map(v => (
                        <option className="bg-background text-foreground" key={v} value={v}>{t(`alerts.operators.${v}`)}</option>
                      ))}
                    </select>
                  </div>
                  <div className="w-28">
                    <Input
                      type="number"
                      step="0.01"
                      inputMode="decimal"
                      placeholder={t("alerts.conditions.valuePlaceholder")}
                      value={c.value}
                      onChange={e => updateCondition(idx, "value", e.target.value)}
                    />
                  </div>
                  {conditions.length > 1 && (
                    <Button type="button" variant="ghost" size="icon" onClick={() => removeCondition(idx)} className="text-muted-foreground hover:text-destructive shrink-0">
                      <Trash2 className="size-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="period">{t("alerts.dialog.period")}</Label>
              <select
                id="period"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={period}
                onChange={e => setPeriod(e.target.value)}
              >
                {PERIOD_VALUES.map(v => (
                  <option className="bg-background text-foreground" key={v} value={v}>{t(`alerts.periods.${v}`)}</option>
                ))}
              </select>
            </div>

            {currentPrice != null && (
              <p className="text-xs text-muted-foreground">
                {t("alerts.dialog.currentPrice", { price: currentPrice.toFixed(2) })}
              </p>
            )}

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>{t("alerts.dialog.cancel")}</Button>
            <Button type="submit" disabled={loading}>
              {loading ? t("alerts.dialog.creating") : t("alerts.dialog.create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ─── Edit Alert Dialog ─── */
function EditAlertDialog({
  open,
  alert,
  onClose,
  onUpdated,
}: {
  open: boolean;
  alert: Alert;
  onClose: () => void;
  onUpdated: (alert: Alert) => void;
}) {
  const { t } = useTranslation();
  const [symbol, setSymbol] = useState(alert.symbol);
  const [selectedSymbol, setSelectedSymbol] = useState(alert.symbol);
  const [symbolName, setSymbolName] = useState(alert.symbol_name || "");
  const [combinator, setCombinator] = useState<"all" | "any">(alert.combinator ?? "all");
  const [conditions, setConditions] = useState<ConditionFormItem[]>(
    (alert.conditions ?? []).map(c => ({ ...c, value: String(c.value) }))
  );
  const [period, setPeriod] = useState(alert.period);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);

  // Fetch current price when a symbol is selected
  useEffect(() => {
    if (!selectedSymbol) {
      setCurrentPrice(null); // eslint-disable-line react-hooks/set-state-in-effect
      return;
    }
    let cancelled = false;
    getStockInfo(selectedSymbol)
      .then(info => { if (!cancelled) setCurrentPrice(info.price || null); })
      .catch(() => { if (!cancelled) setCurrentPrice(null); });
    return () => { cancelled = true; };
  }, [selectedSymbol]);

  const updateCondition = (idx: number, field: string, value: string) => {
    setConditions(prev => prev.map((c, i) => i === idx ? { ...c, [field]: value } : c));
  };

  const addCondition = () => {
    setConditions(prev => [...prev, { metric: "price", operator: "gt", value: "" }]);
  };

  const removeCondition = (idx: number) => {
    setConditions(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim()) { setError(t("alerts.errors.symbolRequired")); return; }

    for (const c of conditions) {
      if (c.value.trim() === "" || isNaN(Number(c.value))) {
        setError(t("alerts.errors.invalidConditionValue"));
        return;
      }
    }
    if (conditions.length === 0) { setError(t("alerts.errors.atLeastOneCondition")); return; }

    setLoading(true);
    setError("");
    try {
      const updated = await updateAlert(alert.id, {
        symbol: symbol.trim().toUpperCase(),
        symbol_name: symbolName || undefined,
        period,
        combinator,
        conditions: conditions.map(c => ({ ...c, value: Number(c.value) })),
      });
      onUpdated(updated);
      onClose();
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("alerts.errors.createFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={o => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("alerts.dialog.editTitle")}</DialogTitle>
          <DialogDescription>
            {t("alerts.dialog.editDescription")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="symbol">{t("alerts.dialog.symbol")}</Label>
              <SymbolSearch
                value={selectedSymbol}
                onSearch={(sym) => {
                  setSelectedSymbol(sym);
                  setSymbol(sym);
                }}
                onSelect={(result) => setSymbolName(result.name)}
              />
            </div>

            <div className="grid gap-2">
              <Label>{t("alerts.dialog.combinator")}</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={combinator === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCombinator("all")}
                >
                  {t("alerts.dialog.combinatorAll")}
                </Button>
                <Button
                  type="button"
                  variant={combinator === "any" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCombinator("any")}
                >
                  {t("alerts.dialog.combinatorAny")}
                </Button>
              </div>
            </div>

            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <Label>{t("alerts.dialog.conditions")}</Label>
                <Button type="button" variant="outline" size="sm" onClick={addCondition}>
                  <Plus className="size-3.5 mr-1" /> {t("alerts.conditions.add")}
                </Button>
              </div>
              {conditions.map((c, idx) => (
                <div key={idx} className="flex items-end gap-2">
                  <div className="flex-1">
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                      value={c.metric}
                      onChange={e => updateCondition(idx, "metric", e.target.value)}
                    >
                      {METRIC_VALUES.map(v => (
                        <option className="bg-background text-foreground" key={v} value={v}>{t(`alerts.metrics.${v}`)}</option>
                      ))}
                    </select>
                  </div>
                  <div className="w-28">
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                      value={c.operator}
                      onChange={e => updateCondition(idx, "operator", e.target.value)}
                    >
                      {OPERATOR_VALUES.map(v => (
                        <option className="bg-background text-foreground" key={v} value={v}>{t(`alerts.operators.${v}`)}</option>
                      ))}
                    </select>
                  </div>
                  <div className="w-28">
                    <Input
                      type="number"
                      step="0.01"
                      inputMode="decimal"
                      placeholder={t("alerts.conditions.valuePlaceholder")}
                      value={c.value}
                      onChange={e => updateCondition(idx, "value", e.target.value)}
                    />
                  </div>
                  {conditions.length > 1 && (
                    <Button type="button" variant="ghost" size="icon" onClick={() => removeCondition(idx)} className="text-muted-foreground hover:text-destructive shrink-0">
                      <Trash2 className="size-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="period">{t("alerts.dialog.period")}</Label>
              <select
                id="period"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={period}
                onChange={e => setPeriod(e.target.value)}
              >
                {PERIOD_VALUES.map(v => (
                  <option className="bg-background text-foreground" key={v} value={v}>{t(`alerts.periods.${v}`)}</option>
                ))}
              </select>
            </div>

            {currentPrice != null && (
              <p className="text-xs text-muted-foreground">
                {t("alerts.dialog.currentPrice", { price: currentPrice.toFixed(2) })}
              </p>
            )}

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>{t("alerts.dialog.cancel")}</Button>
            <Button type="submit" disabled={loading}>
              {loading ? t("alerts.dialog.saving") : t("alerts.dialog.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ─── Notification Settings ─── */
function NotificationSettingsPanel({ settings, onUpdate }: {
  settings: NotificationSettings;
  onUpdate: (s: NotificationSettings) => void;
}) {
  const { t } = useTranslation();
  const [discordWebhook, setDiscordWebhook] = useState(settings.discord_webhook_url || "");
  const [discordEnabled, setDiscordEnabled] = useState(settings.discord_enabled);
  const [emailEnabled, setEmailEnabled] = useState(settings.email_enabled);
  const [emailAddress, setEmailAddress] = useState(settings.email_address || "");
  const [emailSubject, setEmailSubject] = useState(settings.email_subject || "");
  const [emailBody, setEmailBody] = useState(settings.email_body || "");
  // SMTP fields
  const [smtpHost, setSmtpHost] = useState(settings.smtp_host || "");
  const [smtpPort, setSmtpPort] = useState(settings.smtp_port?.toString() ?? "587");
  const [smtpUseTls, setSmtpUseTls] = useState(settings.smtp_use_tls ?? true);
  const [smtpUsername, setSmtpUsername] = useState(settings.smtp_username || "");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFromAddress, setSmtpFromAddress] = useState(settings.smtp_from_address || "");
  const [smtpReplyTo, setSmtpReplyTo] = useState(settings.smtp_reply_to || "");
  const smtpPasswordSet = settings.smtp_password_set ?? false;
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [testingDiscord, setTestingDiscord] = useState(false);
  const [testingSmtp, setTestingSmtp] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    setSaved(false);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        discord_webhook_url: discordWebhook || null,
        discord_enabled: discordEnabled,
        email_enabled: emailEnabled,
        email_address: emailAddress || null,
        email_subject: emailSubject || null,
        email_body: emailBody || null,
        smtp_host: smtpHost || null,
        smtp_port: smtpPort ? Number(smtpPort) : null,
        smtp_use_tls: smtpUseTls,
        smtp_username: smtpUsername || null,
        smtp_from_address: smtpFromAddress || null,
        smtp_reply_to: smtpReplyTo || null,
      };
      if (smtpPassword) {
        payload.smtp_password = smtpPassword;
      }
      const updated = await updateNotificationSettings(payload);
      onUpdate(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("alerts.errors.saveSettingsFailed"));
    } finally {
      setLoading(false);
    }
  };

  const handleTestDiscord = async () => {
    setTestingDiscord(true);
    try {
      await testDiscordWebhook(discordWebhook);
      toast.success("Test message sent — check your Discord channel");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Test failed");
    } finally {
      setTestingDiscord(false);
    }
  };

  const handleTestSmtp = async () => {
    setTestingSmtp(true);
    try {
      const result = await testSmtpSettings(emailAddress);
      if (result.success) {
        toast.success(result.message || "Test email sent successfully");
      } else {
        toast.error(result.message || "Test email failed");
      }
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Test failed");
    } finally {
      setTestingSmtp(false);
    }
  };

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>{t("alerts.settings.title")}</CardTitle>
        <CardDescription>{t("alerts.settings.description")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">

        {/* Discord section */}
        <div className="flex items-center gap-3">
          <Switch
            id="discord-toggle"
            checked={discordEnabled}
            onCheckedChange={setDiscordEnabled}
          />
          <Label htmlFor="discord-toggle">{t("alerts.settings.enableDiscord")}</Label>
        </div>
{discordEnabled && (
          <>
            <div className="grid gap-2">
              <Label htmlFor="webhook">Discord Webhook URL</Label>
              <Input
                id="webhook"
                placeholder="https://discord.com/api/webhooks/..."
                value={discordWebhook}
                onChange={e => setDiscordWebhook(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Get your webhook URL from Discord channel settings → Integrations → Webhooks
              </p>
            </div>
            <Button
              variant="outline"
              disabled={!discordWebhook || testingDiscord}
              onClick={handleTestDiscord}
            >
              {testingDiscord ? "Sending…" : "Send test"}
            </Button>
          </>
        )}

        {/* Email section */}
        <div className="flex items-center gap-3">
          <Switch
            id="email-toggle"
            checked={emailEnabled}
            onCheckedChange={setEmailEnabled}
          />
          <Label htmlFor="email-toggle">Enable Email Notifications</Label>
        </div>

        {emailEnabled && (
          <>
            {/* SMTP subsection */}
            <div className="grid gap-3 rounded-lg border border-border p-4">
              <p className="text-sm font-medium">SMTP Configuration</p>
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <Label htmlFor="smtp-host">Host</Label>
                  <Input
                    id="smtp-host"
                    placeholder="smtp.example.com"
                    value={smtpHost}
                    onChange={e => setSmtpHost(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="smtp-port">Port</Label>
                  <Input
                    id="smtp-port"
                    type="number"
                    placeholder="587"
                    value={smtpPort}
                    onChange={e => setSmtpPort(e.target.value)}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    id="smtp-tls"
                    checked={smtpUseTls}
                    onCheckedChange={setSmtpUseTls}
                  />
                  <Label htmlFor="smtp-tls" className="text-sm font-normal">Use TLS</Label>
                </div>
                <div />
                <div>
                  <Label htmlFor="smtp-username">Username</Label>
                  <Input
                    id="smtp-username"
                    placeholder="user@example.com"
                    value={smtpUsername}
                    onChange={e => setSmtpUsername(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="smtp-password">Password</Label>
                  <Input
                    id="smtp-password"
                    type="password"
                    placeholder={smtpPasswordSet ? "Password is set" : ""}
                    value={smtpPassword}
                    onChange={e => setSmtpPassword(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="smtp-from">From address</Label>
                  <Input
                    id="smtp-from"
                    placeholder="alerts@example.com"
                    value={smtpFromAddress}
                    onChange={e => setSmtpFromAddress(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="smtp-reply-to">Reply-To <span className="text-xs text-muted-foreground">(optional)</span></Label>
                  <Input
                    id="smtp-reply-to"
                    placeholder="reply@example.com"
                    value={smtpReplyTo}
                    onChange={e => setSmtpReplyTo(e.target.value)}
                  />
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={!smtpHost || testingSmtp}
                onClick={handleTestSmtp}
              >
                {testingSmtp ? "Sending…" : "Send test email"}
              </Button>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="email-address">Email Address</Label>
              <Input
                id="email-address"
                type="email"
                placeholder="you@example.com"
                value={emailAddress}
                onChange={e => setEmailAddress(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="email-subject">Email Subject Template</Label>
              <Input
                id="email-subject"
                placeholder="Alert: {symbol} hit {price}"
                value={emailSubject}
                onChange={e => setEmailSubject(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Available tokens: {"{"}symbol{"}"}, {"{"}price{"}"}, {"{"}condition{"}"}, {"{"}threshold{"}"}, {"{"}triggered_at{"}"}. Leave blank for default.
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="email-body">Email Body Template</Label>
              <textarea
                id="email-body"
                className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                placeholder={`{symbol} alert triggered!\n\nCondition: {condition}\nPrice: ${"{"}price{"}"} (threshold: ${"{"}threshold{"}"})\nTriggered at: ${"{"}triggered_at{"}"}`}
                value={emailBody}
                onChange={e => setEmailBody(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Available tokens: {"{"}symbol{"}"}, {"{"}price{"}"}, {"{"}condition{"}"}, {"{"}threshold{"}"}, {"{"}triggered_at{"}"}. Leave blank for default.
              </p>
            </div>
          </>
        )}

        <Button onClick={handleSave} disabled={loading} className="w-fit">
          {loading ? t("alerts.settings.saving") : saved ? t("alerts.settings.saved") : t("alerts.settings.save")}
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}

/* ─── Main Alerts Page ─── */
export default function AlertsPage() {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [triggered, setTriggered] = useState<TriggeredAlert[]>([]);
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("alerts");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [alertsData, triggeredData, settingsData] = await Promise.all([
        getAlerts(),
        getTriggeredAlerts(),
        getNotificationSettings(),
      ]);
      setAlerts(alertsData);
      setTriggered(triggeredData);
      setSettings(settingsData);
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("alerts.errors.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, [loadData]);

  const handleToggle = async (alert: Alert) => {
    try {
      const updated = await updateAlert(alert.id, { enabled: !alert.enabled });
      setAlerts(prev => prev.map(a => a.id === alert.id ? updated : a));
    } catch { /* ignore */ }
  };

  const handleEdit = (alert: Alert) => {
    setEditingAlert(alert);
    setShowEdit(true);
  };

  const handleDelete = async (alertId: number) => {
    if (!confirm(t("alerts.confirmDelete"))) return;
    try {
      await deleteAlert(alertId);
      setAlerts(prev => prev.filter(a => a.id !== alertId));
    } catch { /* ignore */ }
  };

  const handleMarkRead = async (alertId: number) => {
    try {
      const updated = await markTriggeredAlertRead(alertId);
      setTriggered(prev => prev.map(a => a.id === alertId ? updated : a));
    } catch { /* ignore */ }
  };

  const unreadCount = triggered.filter(t => !t.read).length;

  if (loading) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-10 w-full" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("alerts.title")}</h1>
        <Button onClick={() => setShowCreate(true)}>{t("alerts.newAlert")}</Button>
      </div>

        {error && <p className="text-sm text-destructive mb-4">{error}</p>}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="alerts">{t("alerts.tabs.myAlerts", { count: alerts.length })}</TabsTrigger>
            <TabsTrigger value="triggered">
              {t("alerts.tabs.triggered")}
              {unreadCount > 0 && <Badge variant="destructive" className="ml-1.5">{unreadCount}</Badge>}
            </TabsTrigger>
            <TabsTrigger value="settings">{t("alerts.tabs.settings")}</TabsTrigger>
          </TabsList>

          <TabsContent value="alerts">
            {alerts.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                  <Bell className="size-8 text-muted-foreground" />
                  <p className="text-muted-foreground">{t("alerts.empty.noAlerts")}</p>
                  <Button onClick={() => setShowCreate(true)}>{t("alerts.newAlert")}</Button>
                </CardContent>
              </Card>
            ) : (
              <div className="flex flex-col gap-3">
                {alerts.map(alert => (
                  <Card key={alert.id} className={alert.enabled ? "" : "opacity-50"}>
                    <CardContent className="py-4">
                      <div className="flex items-center gap-4">
                        <span className="font-bold text-base min-w-[60px]">{alert.symbol}</span>
                        <span className="text-sm text-muted-foreground truncate flex-1">
                          {alert.symbol_name ? `${alert.symbol_name} · ` : ""}
                          {alert.conditions?.length > 0
                            ? t("alerts.conditionsSummary", {
                                combinator: alert.combinator === "any" ? t("alerts.combinatorAny") : t("alerts.combinatorAll"),
                                count: alert.conditions.length,
                              })
                            : conditionLabel(t, alert.condition_type)
                          }
                        </span>
                        <span className="font-semibold text-sm">
                          {alert.conditions?.length > 0
                            ? ""
                            : alert.condition_type.startsWith("pct") ? `${alert.threshold}%` : `$${fmt(alert.threshold)}`
                          }
                        </span>
                        <span className="text-xs text-muted-foreground uppercase">{alert.period}</span>
                        {(() => {
                          const status = getMarketStatus(alert.symbol);
                          return (
                            <Badge
                              variant={status === "open" ? "default" : "secondary"}
                              className="text-xs shrink-0"
                              title={t(`alerts.marketStatus.${status}`)}
                            >
                              {status === "open" ? "●" : "○"} {t(`alerts.marketStatus.${status}`)}
                            </Badge>
                          );
                        })()}
                        <Switch
                          aria-label={alert.enabled
                            ? t("alerts.aria.disableAlert", { symbol: alert.symbol })
                            : t("alerts.aria.enableAlert", { symbol: alert.symbol })}
                          checked={alert.enabled}
                          onCheckedChange={() => handleToggle(alert)}
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(alert)}
                          className="text-muted-foreground hover:text-foreground"
                          aria-label={t("alerts.aria.editAlert", { symbol: alert.symbol })}
                        >
                          <Pencil />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(alert.id)}
                          className="text-muted-foreground hover:text-destructive"
                          aria-label={t("alerts.aria.deleteAlert", { symbol: alert.symbol })}
                        >
                          <X />
                        </Button>
                      </div>
                      {alert.conditions?.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {alert.conditions.map((c, i) => (
                            <Badge key={c.id || i} variant="secondary" className="text-xs">
                              {metricLabel(t, c.metric)} {operatorLabel(t, c.operator)} {c.value}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="triggered">
            {triggered.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                  <CheckCircle2 className="size-8 text-muted-foreground" />
                  <p className="text-muted-foreground">{t("alerts.empty.noTriggered")}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="flex flex-col gap-3">
                {triggered.map(alert => (
                  <Card
                    key={alert.id}
                    role={alert.read ? undefined : "button"}
                    tabIndex={alert.read ? -1 : 0}
                    aria-label={alert.read ? undefined : t("alerts.aria.markRead", { symbol: alert.symbol })}
                    className={`transition-colors ${alert.read ? "opacity-70" : "cursor-pointer border-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"}`}
                    onClick={() => !alert.read && handleMarkRead(alert.id)}
                    onKeyDown={(e) => {
                      if (!alert.read && (e.key === "Enter" || e.key === " ")) {
                        e.preventDefault();
                        handleMarkRead(alert.id);
                      }
                    }}
                  >
                    <CardContent className="py-4">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-bold">{alert.symbol}</span>
                        {alert.symbol_name && (
                          <span className="text-sm text-muted-foreground truncate">{alert.symbol_name}</span>
                        )}
                        <span className="text-sm text-muted-foreground">{conditionLabel(t, alert.condition_type)}</span>
                        {!alert.read && (
                          <span className="ml-auto flex items-center">
                            <span className="inline-block size-2 rounded-full bg-primary" aria-hidden="true" />
                            <span className="sr-only">{t("alerts.unread")}</span>
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {t("alerts.triggeredAt", {
                          price: fmt(alert.trigger_price),
                          threshold: fmt(alert.threshold_value),
                        })}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(alert.triggered_at).toLocaleString()}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="settings">
            {settings && (
              <NotificationSettingsPanel settings={settings} onUpdate={setSettings} />
            )}
          </TabsContent>
        </Tabs>

      <CreateAlertDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={alert => setAlerts(prev => [alert, ...prev])}
      />

      {editingAlert && (
        <EditAlertDialog
          open={showEdit}
          alert={editingAlert}
          onClose={() => { setShowEdit(false); setEditingAlert(null); }}
          onUpdated={(updated) => {
            setAlerts(prev => prev.map(a => a.id === updated.id ? updated : a));
            setShowEdit(false);
            setEditingAlert(null);
          }}
        />
      )}
    </div>
  );
}
