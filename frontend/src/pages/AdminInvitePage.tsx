import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Copy, Check, X, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/sonner";
import { copyText } from "@/lib/clipboard";

const API = import.meta.env.VITE_API_URL || "";

interface InviteCode {
  id: number;
  code: string;
  created_by: string;
  used_by: string | null;
  used_at: string | null;
  expires_at: string;
  is_active: boolean;
  created_at: string;
  email: string | null;
  invite_link: string | null;
}

interface InviteCodeListResponse {
  codes: InviteCode[];
  total: number;
}

interface CreateInviteCodeRequest {
  expires_in_days: number;
  email?: string | null;
}

interface AccountRequest {
  id: number;
  email: string;
  note: string | null;
  status: "pending" | "approved" | "denied";
  invite_id: number | null;
  created_at: string;
}

interface AccountRequestListResponse {
  requests: AccountRequest[];
  total: number;
}

/* ─── Create Invite Code Dialog ─── */
function CreateInviteCodeDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (link: string) => void;
}) {
  const { t } = useTranslation();
  const [expiresInDays, setExpiresInDays] = useState("7");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const days = parseInt(expiresInDays, 10);
    if (isNaN(days) || days < 1 || days > 365) {
      setError(t("adminInvite.form.validationRange"));
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(API + "/api/admin/invite-codes", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` },
        body: JSON.stringify({ expires_in_days: days, email: email || null } as CreateInviteCodeRequest),
      });
      if (!res.ok) {
        const data = await res.json() as { detail?: string };
        throw new Error(data.detail || t("adminInvite.errors.create"));
      }
      const data = await res.json() as InviteCode;
      onCreated(data.invite_link ?? data.code);
      onClose();
    } catch (err: unknown) {
      setError((err as Error).message || t("adminInvite.errors.create"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={o => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("adminInvite.form.dialogTitle")}</DialogTitle>
          <DialogDescription>
            {t("adminInvite.form.dialogDescription")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="expires">{t("adminInvite.form.expiresLabel")}</Label>
              <Input
                id="expires"
                type="number"
                min="1"
                max="365"
                value={expiresInDays}
                onChange={e => setExpiresInDays(e.target.value)}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                {t("adminInvite.form.expiresHint")}
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="invite-email">{t("adminInvite.form.emailLabel")}</Label>
              <Input
                id="invite-email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
              <p className="text-xs text-muted-foreground">{t("adminInvite.form.emailHint")}</p>
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>{t("adminInvite.form.cancel")}</Button>
            <Button type="submit" disabled={loading}>
              {loading ? t("adminInvite.form.generating") : t("adminInvite.form.submit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ─── Copy Button ─── */
function CopyButton({ value }: { value: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    const ok = await copyText(value);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } else {
      toast.error(t("adminInvite.copy.errorTitle"), { description: t("adminInvite.copy.errorDescription") });
    }
  };
  return (
    <Button variant="ghost" size="icon" onClick={handleCopy} aria-label={t("adminInvite.copy.ariaLabel")}>
      {copied ? <Check className="size-4 text-up" /> : <Copy className="size-4" />}
    </Button>
  );
}

/* ─── Pending Account Requests ─── */
function RequestsSection() {
  const { t } = useTranslation();
  const [requests, setRequests] = useState<AccountRequest[]>([]);
  const [approvedLink, setApprovedLink] = useState<string | null>(null);
  const [error, setError] = useState("");

  const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` });

  const load = useCallback(async () => {
    try {
      const res = await fetch(API + "/api/admin/account-requests", { headers: authHeader() });
      if (!res.ok) return;
      const data = await res.json() as AccountRequestListResponse;
      setRequests(data.requests);
    } catch { /* section is best-effort; invite list below still works */ }
  }, []);

  useEffect(() => {
    (async () => {
      await load();
    })();
  }, [load]);

  const handleApprove = async (id: number) => {
    setError("");
    try {
      const res = await fetch(API + `/api/admin/account-requests/${id}/approve`, {
        method: "POST",
        headers: authHeader(),
      });
      if (!res.ok) {
        const data = await res.json() as { detail?: string };
        throw new Error(data.detail);
      }
      const data = await res.json() as { invite_link: string; email_sent: boolean };
      setApprovedLink(data.invite_link);
      void load();
    } catch (err: unknown) {
      setError((err as Error).message || t("adminInvite.requests.errors.approve"));
    }
  };

  const handleDeny = async (id: number) => {
    if (!confirm(t("adminInvite.requests.confirm.deny"))) return;
    setError("");
    try {
      const res = await fetch(API + `/api/admin/account-requests/${id}/deny`, {
        method: "POST",
        headers: authHeader(),
      });
      if (!res.ok) {
        const data = await res.json() as { detail?: string };
        throw new Error(data.detail);
      }
      void load();
    } catch (err: unknown) {
      setError((err as Error).message || t("adminInvite.requests.errors.deny"));
    }
  };

  const pending = requests.filter(r => r.status === "pending");
  if (requests.length === 0) return null;

  return (
    <div className="mb-6">
      <h2 className="mb-3 text-lg font-medium">
        {t("adminInvite.requests.title")}
        {pending.length > 0 && (
          <span className="ml-2 rounded-full bg-primary/15 px-2 py-0.5 text-xs text-primary">{pending.length}</span>
        )}
      </h2>
      {error && (
        <Card className="mb-3 border-destructive/40 bg-destructive/10">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}
      {approvedLink && (
        <Card className="mb-3 border-up/40 bg-up/10">
          <CardContent className="flex items-center justify-between py-3">
            <div className="flex items-center gap-2 min-w-0">
              <Check className="size-4 text-up shrink-0" />
              <span className="text-sm font-medium shrink-0">{t("adminInvite.requests.approvedLinkLabel")}</span>
              <code className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono truncate">{approvedLink}</code>
            </div>
            <CopyButton value={approvedLink} />
          </CardContent>
        </Card>
      )}
      <div className="flex flex-col gap-3">
        {requests.map(req => (
          <Card key={req.id} className={req.status !== "pending" ? "opacity-60" : ""}>
            <CardContent className="flex items-center gap-4 py-4">
              <div className="flex flex-col gap-1 flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{req.email}</span>
                  {req.status !== "pending" && (
                    <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                      {t(`adminInvite.requests.status.${req.status}`)}
                    </span>
                  )}
                </div>
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span>{t("adminInvite.table.created", { date: new Date(req.created_at).toLocaleDateString() })}</span>
                  {req.note && <span className="truncate">{req.note}</span>}
                </div>
              </div>
              {req.status === "pending" && (
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" onClick={() => handleApprove(req.id)}>
                    {t("adminInvite.requests.approve")}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleDeny(req.id)}>
                    {t("adminInvite.requests.deny")}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ─── Main Admin Invite Page ─── */
export default function AdminInvitePage() {
  const { t } = useTranslation();
  const [codes, setCodes] = useState<InviteCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newLink, setNewLink] = useState<string | null>(null);

  const loadCodes = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(API + "/api/admin/invite-codes", {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` },
      });
      if (!res.ok) {
        const data = await res.json() as { detail?: string };
        throw new Error(data.detail || t("adminInvite.errors.load"));
      }
      const data = await res.json() as InviteCodeListResponse;
      setCodes(data.codes);
    } catch (err: unknown) {
      setError((err as Error).message || t("adminInvite.errors.load"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    (async () => {
      await loadCodes();
    })();
  }, [loadCodes]);

  const handleDeactivate = async (codeId: number) => {
    if (!confirm(t("adminInvite.confirm.deactivate"))) return;
    try {
      const res = await fetch(API + "/api/admin/invite-codes/" + codeId, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` },
      });
      if (!res.ok) {
        const data = await res.json() as { detail?: string };
        throw new Error(data.detail || t("adminInvite.errors.deactivate"));
      }
      setCodes(prev => prev.map(c => c.id === codeId ? { ...c, is_active: false } : c));
    } catch (err: unknown) {
      alert((err as Error).message || t("adminInvite.errors.deactivate"));
    }
  };

  const handleDelete = async (codeId: number) => {
    if (!confirm(t("adminInvite.confirm.delete"))) return;
    try {
      const res = await fetch(API + "/api/admin/invite-codes/" + codeId + "/permanent", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` },
      });
      if (!res.ok) {
        const data = await res.json() as { detail?: string };
        throw new Error(data.detail || t("adminInvite.errors.delete"));
      }
      void loadCodes();
    } catch (err: unknown) {
      setError((err as Error).message || t("adminInvite.errors.delete"));
    }
  };

  const handleLinkCreated = (link: string) => {
    setNewLink(link);
    void loadCodes();
  };

  const isExpired = (expiresAt: string) => new Date(expiresAt) < new Date();

  if (loading) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        <Skeleton className="h-9 w-60" />
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
        <div>
          <h1 className="text-2xl font-semibold">{t("adminInvite.title")}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("adminInvite.subtitle")}
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="size-4 mr-1.5" />
          {t("adminInvite.generateCode")}
        </Button>
      </div>

      <RequestsSection />

      {error && (
        <Card className="mb-4 border-destructive/40 bg-destructive/10">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {newLink && (
        <Card className="mb-4 border-up/40 bg-up/10">
          <CardContent className="flex items-center justify-between py-3">
            <div className="flex items-center gap-2">
              <Check className="size-4 text-up" />
              <span className="text-sm font-medium">{t("adminInvite.newCodeLabel")}</span>
              <code className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono">{newLink}</code>
            </div>
            <CopyButton value={newLink} />
          </CardContent>
        </Card>
      )}

      {codes.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-muted-foreground">{t("adminInvite.empty.message")}</p>
            <Button onClick={() => setShowCreate(true)}>{t("adminInvite.empty.action")}</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {codes.map(code => (
            <Card
              key={code.id}
              className={!code.is_active || isExpired(code.expires_at) ? "opacity-60" : ""}
            >
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex flex-col gap-1 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <code className="rounded bg-muted px-2 py-0.5 text-sm font-mono truncate max-w-[22rem]" title={code.invite_link ?? code.code}>
                      {code.invite_link ?? code.code}
                    </code>
                    <CopyButton value={code.invite_link ?? code.code} />
                    {code.email && <span>{code.email}</span>}
                    {code.used_by && (
                      <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                        {t("adminInvite.table.used")}
                      </span>
                    )}
                    {!code.is_active && (
                      <span className="rounded-full bg-destructive/20 px-2 py-0.5 text-xs text-destructive">
                        {t("adminInvite.table.deactivated")}
                      </span>
                    )}
                    {isExpired(code.expires_at) && (
                      <span className="rounded-full bg-destructive/20 px-2 py-0.5 text-xs text-destructive">
                        {t("adminInvite.table.expired")}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-4 text-xs text-muted-foreground">
                    <span>
                      {t("adminInvite.table.created", { date: new Date(code.created_at).toLocaleDateString() })}
                    </span>
                    <span>
                      {t("adminInvite.table.expires", { date: new Date(code.expires_at).toLocaleDateString() })}
                    </span>
                    {code.used_by && (
                      <span>{t("adminInvite.table.usedBy", { user: code.used_by })}</span>
                    )}
                  </div>
                </div>
                {code.is_active && !isExpired(code.expires_at) ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeactivate(code.id)}
                    className="text-muted-foreground hover:text-destructive shrink-0"
                    aria-label={t("adminInvite.table.deactivateAriaLabel")}
                  >
                    <X className="size-4" />
                  </Button>
                ) : (!code.is_active || isExpired(code.expires_at)) && !code.used_by ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(code.id)}
                    className="text-muted-foreground hover:text-destructive shrink-0"
                    aria-label={t("adminInvite.table.deleteAriaLabel")}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateInviteCodeDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={handleLinkCreated}
      />
    </div>
  );
}
