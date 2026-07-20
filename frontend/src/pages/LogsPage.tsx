import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, ChevronDown, ChevronRight, Search, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from "@/components/ui/tabs";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/sonner";
import { fetchLogs, type LogEntry } from "@/api/adminLogsApi";
import { fetchAuditLogs, type AuditLogEntry } from "@/api/adminAuditLogsApi";
import { fetchAccessLogs, type AccessLogEntry } from "@/api/adminAccessLogsApi";
import { copyText } from "@/lib/clipboard";

/* ── System log helpers ────────────────────────────────────── */

const LEVELS = ["", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: "bg-gray-500/20 text-gray-300 hover:bg-gray-500/30",
  INFO: "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30",
  WARNING: "bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30",
  ERROR: "bg-red-500/20 text-red-300 hover:bg-red-500/30",
  CRITICAL: "bg-purple-500/20 text-purple-300 hover:bg-purple-500/30",
};

function LevelBadge({ level }: { level: string }) {
  const colorClass = LEVEL_COLORS[level] ?? "bg-secondary text-secondary-foreground";
  return (
    <Badge variant="outline" className={`font-mono text-[10px] ${colorClass} border-0`}>
      {level}
    </Badge>
  );
}

/* ── Audit log helpers ─────────────────────────────────────── */

const ACTION_COLORS: Record<string, string> = {
  create: "bg-green-500/20 text-green-300 hover:bg-green-500/30",
  created: "bg-green-500/20 text-green-300 hover:bg-green-500/30",
  update: "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30",
  updated: "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30",
  delete: "bg-red-500/20 text-red-300 hover:bg-red-500/30",
  deleted: "bg-red-500/20 text-red-300 hover:bg-red-500/30",
  login: "bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30",
  logout: "bg-gray-500/20 text-gray-300 hover:bg-gray-500/30",
};

function AuditActionBadge({ action }: { action: string }) {
  const colorClass = ACTION_COLORS[action.toLowerCase()] ?? "bg-secondary text-secondary-foreground";
  return (
    <Badge variant="outline" className={`font-mono text-[10px] ${colorClass} border-0`}>
      {action}
    </Badge>
  );
}

/* ── Access log helpers ────────────────────────────────────── */

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-green-500/20 text-green-300 hover:bg-green-500/30",
  POST: "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30",
  PUT: "bg-orange-500/20 text-orange-300 hover:bg-orange-500/30",
  PATCH: "bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30",
  DELETE: "bg-red-500/20 text-red-300 hover:bg-red-500/30",
};

function MethodBadge({ method }: { method: string }) {
  const colorClass = METHOD_COLORS[method.toUpperCase()] ?? "bg-secondary text-secondary-foreground";
  return (
    <Badge variant="outline" className={`font-mono text-[10px] ${colorClass} border-0`}>
      {method}
    </Badge>
  );
}

function statusColor(status: number): string {
  if (status >= 200 && status < 300) return "bg-green-500/20 text-green-300 hover:bg-green-500/30";
  if (status >= 300 && status < 400) return "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30";
  if (status >= 400 && status < 500) return "bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30";
  if (status >= 500) return "bg-red-500/20 text-red-300 hover:bg-red-500/30";
  return "bg-secondary text-secondary-foreground";
}

function StatusBadge({ status }: { status: number }) {
  return (
    <Badge variant="outline" className={`font-mono text-[10px] ${statusColor(status)} border-0`}>
      {status}
    </Badge>
  );
}

/* ── Copy helper ───────────────────────────────────────────── */

function CopyButton({ data }: { data: unknown }) {
  const { t } = useTranslation();
  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const ok = await copyText(JSON.stringify(data, null, 2));
    if (ok) {
      toast(t("logs.copy.toastTitle"), { description: t("logs.copy.toastDescription") });
    } else {
      toast.error(t("logs.copy.errorTitle"), { description: t("logs.copy.errorDescription") });
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="ml-auto text-muted-foreground hover:text-foreground transition-colors"
      title={t("logs.copy.buttonTitle")}
    >
      <Copy className="size-3.5" />
    </button>
  );
}

/* ── System Logs Tab ───────────────────────────────────────── */

function SystemLogsTab({ autoRefresh }: { autoRefresh: boolean }) {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [level, setLevel] = useState("");
  const [search, setSearch] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadLogs = useCallback(async () => {
    setError("");
    try {
      const data = await fetchLogs({
        level: level || undefined,
        search: search || undefined,
        limit: 500,
      });
      setLogs(data.logs);
      setTotal(data.total);
    } catch (err: unknown) {
      setError((err as Error).message || t("logs.errors.loadSystem"));
    } finally {
      setLoading(false);
    }
  }, [level, search]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadLogs();
  }, [loadLogs]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(loadLogs, 5000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, loadLogs]);

  const handleRefresh = () => {
    setLoading(true);
    loadLogs();
  };

  return (
    <div>
      <Card className="mb-4">
        <CardContent className="flex flex-wrap items-end gap-3 py-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="sys-level" className="text-xs text-muted-foreground">{t("logs.filters.level")}</Label>
            <Select value={level} onValueChange={setLevel}>
              <SelectTrigger id="sys-level" className="w-32">
                <SelectValue placeholder={t("logs.filters.allLevels")} />
              </SelectTrigger>
              <SelectContent>
                {LEVELS.map((l) => (
                  <SelectItem key={l} value={l}>{l || t("logs.filters.allLevels")}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
            <Label htmlFor="sys-search" className="text-xs text-muted-foreground">{t("logs.filters.search")}</Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                id="sys-search"
                placeholder={t("logs.filters.searchSystemPlaceholder")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`size-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            {t("logs.refresh")}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Card className="mb-4 border-destructive/40 bg-destructive/10">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full rounded-md" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-muted-foreground">{t("logs.empty.system")}</p>
          </CardContent>
        </Card>
      ) : (
        <div>
          <p className="text-xs text-muted-foreground mb-2">{t("logs.entries", { count: total })}</p>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                  <th className="py-2.5 px-3 w-[170px]">{t("logs.table.timestamp")}</th>
                  <th className="py-2.5 px-3 w-[90px]">{t("logs.table.level")}</th>
                  <th className="py-2.5 px-3">{t("logs.table.logger")}</th>
                  <th className="py-2.5 px-3">{t("logs.table.message")}</th>
                  <th className="py-2.5 px-3 w-14" />
                </tr>
              </thead>
              <tbody>
                {logs.map((entry, i) => (
                  <SystemLogRow key={`${entry.timestamp}-${i}`} entry={entry} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SystemLogRow({ entry }: { entry: LogEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="border-b border-border hover:bg-accent/50 cursor-pointer text-sm"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-2 px-3 text-muted-foreground font-mono text-[11px] whitespace-nowrap">
          {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "—"}
        </td>
        <td className="py-2 px-3"><LevelBadge level={entry.level} /></td>
        <td className="py-2 px-3 text-muted-foreground font-mono text-[11px] max-w-[160px] truncate">
          {entry.logger ?? "—"}
        </td>
        <td className="py-2 px-3 text-foreground max-w-xs truncate">{entry.message ?? "—"}</td>
        <td className="py-2 px-3">
          <div className="flex items-center gap-1">
            <CopyButton data={entry} />
            {expanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="bg-muted/30">
          <td colSpan={5} className="p-3">
            <pre className="rounded bg-background p-3 text-xs font-mono overflow-auto max-h-96 whitespace-pre-wrap break-all">
              {JSON.stringify(entry, null, 2)}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}

/* ── Audit Logs Tab ────────────────────────────────────────── */

function AuditLogsTab({ autoRefresh }: { autoRefresh: boolean }) {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [search, setSearch] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadLogs = useCallback(async () => {
    setError("");
    try {
      const data = await fetchAuditLogs({
        action: actionFilter || undefined,
        search: search || undefined,
        limit: 500,
      });
      setLogs(data.logs);
      setTotal(data.total);
    } catch (err: unknown) {
      setError((err as Error).message || t("logs.errors.loadAudit"));
    } finally {
      setLoading(false);
    }
  }, [actionFilter, search]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadLogs();
  }, [loadLogs]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(loadLogs, 5000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, loadLogs]);

  const handleRefresh = () => {
    setLoading(true);
    loadLogs();
  };

  return (
    <div>
      <Card className="mb-4">
        <CardContent className="flex flex-wrap items-end gap-3 py-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="audit-action" className="text-xs text-muted-foreground">{t("logs.filters.action")}</Label>
            <Select value={actionFilter} onValueChange={setActionFilter}>
              <SelectTrigger id="audit-action" className="w-36">
                <SelectValue placeholder={t("logs.filters.allActions")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">{t("logs.filters.allActions")}</SelectItem>
                <SelectItem value="create">create</SelectItem>
                <SelectItem value="update">update</SelectItem>
                <SelectItem value="delete">delete</SelectItem>
                <SelectItem value="login">login</SelectItem>
                <SelectItem value="logout">logout</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
            <Label htmlFor="audit-search" className="text-xs text-muted-foreground">{t("logs.filters.search")}</Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                id="audit-search"
                placeholder={t("logs.filters.searchAuditPlaceholder")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`size-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            {t("logs.refresh")}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Card className="mb-4 border-destructive/40 bg-destructive/10">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full rounded-md" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-muted-foreground">{t("logs.empty.audit")}</p>
          </CardContent>
        </Card>
      ) : (
        <div>
          <p className="text-xs text-muted-foreground mb-2">{t("logs.entries", { count: total })}</p>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                  <th className="py-2.5 px-3 w-[170px]">{t("logs.table.timestamp")}</th>
                  <th className="py-2.5 px-3 w-[80px]">{t("logs.table.actor")}</th>
                  <th className="py-2.5 px-3 w-[90px]">{t("logs.table.action")}</th>
                  <th className="py-2.5 px-3">{t("logs.table.target")}</th>
                  <th className="py-2.5 px-3 w-[130px]">{t("logs.table.ip")}</th>
                  <th className="py-2.5 px-3 w-14" />
                </tr>
              </thead>
              <tbody>
                {logs.map((entry) => (
                  <AuditLogRow key={entry.id} entry={entry} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function AuditLogRow({ entry }: { entry: AuditLogEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="border-b border-border hover:bg-accent/50 cursor-pointer text-sm"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-2 px-3 text-muted-foreground font-mono text-[11px] whitespace-nowrap">
          {entry.created_at ? new Date(entry.created_at).toLocaleString() : "—"}
        </td>
        <td className="py-2 px-3 font-mono text-[11px]">{entry.actor_id ?? "—"}</td>
        <td className="py-2 px-3"><AuditActionBadge action={entry.action} /></td>
        <td className="py-2 px-3 text-foreground max-w-xs truncate">{entry.target ?? "—"}</td>
        <td className="py-2 px-3 text-muted-foreground font-mono text-[11px]">{entry.ip ?? "—"}</td>
        <td className="py-2 px-3">
          <div className="flex items-center gap-1">
            <CopyButton data={entry} />
            {expanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="bg-muted/30">
          <td colSpan={6} className="p-3">
            <pre className="rounded bg-background p-3 text-xs font-mono overflow-auto max-h-96 whitespace-pre-wrap break-all">
              {JSON.stringify(entry, null, 2)}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}

/* ── Access Logs Tab ───────────────────────────────────────── */

const HTTP_METHODS = ["", "GET", "POST", "PUT", "PATCH", "DELETE"];

function AccessLogsTab({ autoRefresh }: { autoRefresh: boolean }) {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<AccessLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [method, setMethod] = useState("");
  const [statusMin, setStatusMin] = useState("");
  const [statusMax, setStatusMax] = useState("");
  const [search, setSearch] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadLogs = useCallback(async () => {
    setError("");
    try {
      const data = await fetchAccessLogs({
        method: method || undefined,
        status_min: statusMin ? Number(statusMin) : undefined,
        status_max: statusMax ? Number(statusMax) : undefined,
        search: search || undefined,
        limit: 500,
      });
      setLogs(data.logs);
      setTotal(data.total);
    } catch (err: unknown) {
      setError((err as Error).message || t("logs.errors.loadAccess"));
    } finally {
      setLoading(false);
    }
  }, [method, statusMin, statusMax, search]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadLogs();
  }, [loadLogs]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(loadLogs, 5000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, loadLogs]);

  const handleRefresh = () => {
    setLoading(true);
    loadLogs();
  };

  return (
    <div>
      <Card className="mb-4">
        <CardContent className="flex flex-wrap items-end gap-3 py-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="acc-method" className="text-xs text-muted-foreground">{t("logs.filters.method")}</Label>
            <Select value={method} onValueChange={setMethod}>
              <SelectTrigger id="acc-method" className="w-28">
                <SelectValue placeholder={t("logs.filters.all")} />
              </SelectTrigger>
              <SelectContent>
                {HTTP_METHODS.map((m) => (
                  <SelectItem key={m} value={m}>{m || t("logs.filters.all")}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="acc-status-min" className="text-xs text-muted-foreground">{t("logs.filters.statusMin")}</Label>
            <Input
              id="acc-status-min"
              type="number"
              placeholder={t("logs.filters.minPlaceholder")}
              value={statusMin}
              onChange={(e) => setStatusMin(e.target.value)}
              className="w-20"
              min={100}
              max={599}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="acc-status-max" className="text-xs text-muted-foreground">{t("logs.filters.statusMax")}</Label>
            <Input
              id="acc-status-max"
              type="number"
              placeholder={t("logs.filters.maxPlaceholder")}
              value={statusMax}
              onChange={(e) => setStatusMax(e.target.value)}
              className="w-20"
              min={100}
              max={599}
            />
          </div>
          <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
            <Label htmlFor="acc-search" className="text-xs text-muted-foreground">{t("logs.filters.search")}</Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                id="acc-search"
                placeholder={t("logs.filters.searchAccessPlaceholder")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`size-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            {t("logs.refresh")}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Card className="mb-4 border-destructive/40 bg-destructive/10">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full rounded-md" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-muted-foreground">{t("logs.empty.access")}</p>
          </CardContent>
        </Card>
      ) : (
        <div>
          <p className="text-xs text-muted-foreground mb-2">{t("logs.entries", { count: total })}</p>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                  <th className="py-2.5 px-3 w-[170px]">{t("logs.table.timestamp")}</th>
                  <th className="py-2.5 px-3 w-[130px]">{t("logs.table.ip")}</th>
                  <th className="py-2.5 px-3 w-[80px]">{t("logs.table.method")}</th>
                  <th className="py-2.5 px-3">{t("logs.table.path")}</th>
                  <th className="py-2.5 px-3 w-[70px]">{t("logs.table.status")}</th>
                  <th className="py-2.5 px-3 w-[60px]">{t("logs.table.ms")}</th>
                  <th className="py-2.5 px-3 w-14" />
                </tr>
              </thead>
              <tbody>
                {logs.map((entry, i) => (
                  <AccessLogRow key={`${entry.timestamp}-${i}`} entry={entry} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function AccessLogRow({ entry }: { entry: AccessLogEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="border-b border-border hover:bg-accent/50 cursor-pointer text-sm"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-2 px-3 text-muted-foreground font-mono text-[11px] whitespace-nowrap">
          {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "—"}
        </td>
        <td className="py-2 px-3 text-muted-foreground font-mono text-[11px]">{entry.ip ?? "—"}</td>
        <td className="py-2 px-3"><MethodBadge method={entry.method} /></td>
        <td className="py-2 px-3 text-foreground max-w-[200px] truncate font-mono text-[12px]">
          {entry.path ?? "—"}
        </td>
        <td className="py-2 px-3"><StatusBadge status={entry.status} /></td>
        <td className="py-2 px-3 text-muted-foreground font-mono text-[11px]">{entry.ms ?? "—"}</td>
        <td className="py-2 px-3">
          <div className="flex items-center gap-1">
            <CopyButton data={entry} />
            {expanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="bg-muted/30">
          <td colSpan={7} className="p-3">
            <pre className="rounded bg-background p-3 text-xs font-mono overflow-auto max-h-96 whitespace-pre-wrap break-all">
              {JSON.stringify(entry, null, 2)}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}

/* ── Unified Logs Page ─────────────────────────────────────── */

export default function LogsPage() {
  const { t } = useTranslation();
  const [autoRefresh, setAutoRefresh] = useState(false);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t("logs.title")}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("logs.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Label htmlFor="logs-auto-refresh" className="text-sm text-muted-foreground">
              {t("logs.autoRefresh")}
            </Label>
            <Switch
              id="logs-auto-refresh"
              checked={autoRefresh}
              onCheckedChange={setAutoRefresh}
            />
          </div>
        </div>
      </div>

      <Tabs defaultValue="system">
        <TabsList>
          <TabsTrigger value="system">{t("logs.tabs.system")}</TabsTrigger>
          <TabsTrigger value="audit">{t("logs.tabs.audit")}</TabsTrigger>
          <TabsTrigger value="access">{t("logs.tabs.access")}</TabsTrigger>
        </TabsList>
        <TabsContent value="system">
          <SystemLogsTab autoRefresh={autoRefresh} />
        </TabsContent>
        <TabsContent value="audit">
          <AuditLogsTab autoRefresh={autoRefresh} />
        </TabsContent>
        <TabsContent value="access">
          <AccessLogsTab autoRefresh={autoRefresh} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
