import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";

/** Drill into any FastAPI error shape and return a human-readable message.
 *  Handles: string detail, Pydantic validation detail array, {detail:string} */
async function extractError(res: Response, fallback: string): Promise<string> {
  try {
    const d = await res.json();
    // Pydantic 422: detail is ValidationError[]
    if (Array.isArray(d.detail)) {
      return d.detail[0]?.msg || fallback;
    }
    // Plain string detail: HTTPException raised by app code
    if (typeof d.detail === "string") return d.detail;
    // Fallback for unexpected shapes
    return d.detail || fallback;
  } catch {
    return fallback;
  }
}
import { useTheme } from "../hooks/useTheme";
import { COMMON_TIMEZONES } from "../context/timezones";
import { useAuth } from "../hooks/useAuth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "../components/ui/dialog";
import { Loader2, Key, Pencil } from "lucide-react";
import { toast } from "@/components/ui/sonner";
import { APP_VERSION, RELEASE_URL, RELEASE_API_URL } from "../lib/version";
import { fmtDate } from "../lib/format";
import ReactMarkdown from "react-markdown";

export default function SettingsPage() {
  const { t } = useTranslation();
  const { theme, toggleTheme, timezone, setTimezone } = useTheme();
  const { user } = useAuth();
  const [yfStatus, setYfStatus] = useState<"loading" | "ok" | "error">("loading");
  const [yfMessage, setYfMessage] = useState("");
  const [users, setUsers] = useState<Array<{
    id: string;
    email: string;
    username: string;
    created_at?: string;
    last_login_at?: string;
    is_admin: boolean;
    is_active: boolean;
  }>>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addUsername, setAddUsername] = useState("");
  const [addPassword, setAddPassword] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; username: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [resetTarget, setResetTarget] = useState<{ id: string; username: string } | null>(null);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetResult, setResetResult] = useState<string | null>(null);
  const [resetError, setResetError] = useState("");
  const [editEmailOpen, setEditEmailOpen] = useState(false);
  const [editEmailTarget, setEditEmailTarget] = useState<{ id: string; email: string; is_admin: boolean; is_active: boolean } | null>(null);
  const [editEmail, setEditEmail] = useState("");
  const [editEmailLoading, setEditEmailLoading] = useState(false);
  const [editEmailError, setEditEmailError] = useState("");
  const [releaseNotes, setReleaseNotes] = useState<string | null>(null);

  const isAdmin = user?.is_admin === true;

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    fetch(`${import.meta.env.VITE_API_URL || ""}/api/mcp/yf-health`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => res.json() as Promise<{ status?: string; message?: string }>)
      .then(data => {
        if (data.status === "ok") {
          setYfStatus("ok");
          setYfMessage(data.message ?? t("settings.dataSource.working"));
        } else {
          setYfStatus("error");
          setYfMessage(data.message ?? t("settings.dataSource.checkFailed"));
        }
      })
      .catch(() => {
        setYfStatus("error");
        setYfMessage(t("settings.dataSource.unreachable"));
      });
  }, [t]);

  useEffect(() => {
    if (!isAdmin) return;
    const token = localStorage.getItem("access_token");
    let ignore = false;
    fetch(`${import.meta.env.VITE_API_URL || ""}/api/auth/users`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => res.json())
      .then(data => { if (!ignore) setUsers(data.users ?? []); })
      .catch(() => { if (!ignore) setUsers([]); })
      .finally(() => { if (!ignore) setUsersLoading(false); });
    return () => { ignore = true; };
  }, [isAdmin]);

  useEffect(() => {
    if (releaseNotes !== null) return; // cached, skip
    let ignore = false;
    fetch(RELEASE_API_URL)
      .then(res => {
        if (!res.ok) throw new Error("not found");
        return res.json();
      })
      .then(data => {
        if (!ignore && data.body) setReleaseNotes(data.body);
      })
      .catch(() => {
        if (!ignore) setReleaseNotes(""); // graceful degradation — empty string
      });
    return () => { ignore = true; };
  }, []);

  const addUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddLoading(true);
    setAddError("");
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/auth/register`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ email: addEmail, username: addUsername, password: addPassword }),
      });
      if (!res.ok) {
        throw new Error(await extractError(res, t("settings.errors.addUser")));
      }
      const newUser = await res.json();
      setUsers(prev => [...prev, newUser]);
      setAddOpen(false);
      setAddEmail("");
      setAddUsername("");
      setAddPassword("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("settings.errors.addUser");
      setAddError(msg);
    } finally {
      setAddLoading(false);
    }
  };

  const resetUserPassword = async () => {
    if (!resetTarget) return;
    setResetLoading(true);
    setResetError("");
    setResetResult(null);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/auth/users/${resetTarget.id}/reset-password`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(typeof d.detail === "string" ? d.detail : d.detail?.[0]?.msg || t("settings.errors.resetFailed"));
      }
      const data = await res.json();
      setResetResult(data.password);
    } catch (err: unknown) {
      setResetError((err as Error).message);
    } finally {
      setResetLoading(false);
    }
  };

  const openEditEmail = (user: { id: string; email: string; is_admin: boolean; is_active: boolean }) => {
    setEditEmailTarget(user);
    setEditEmail(user.email);
    setEditEmailError("");
    setEditEmailOpen(true);
  };

  const editUserEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editEmailTarget) return;
    setEditEmailLoading(true);
    setEditEmailError("");
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/auth/users/${editEmailTarget.id}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ email: editEmail, is_admin: editEmailTarget.is_admin, is_active: editEmailTarget.is_active }),
      });
      if (!res.ok) {
        throw new Error(await extractError(res, t("settings.errors.updateEmail")));
      }
      setUsers(prev => prev.map(u => u.id === editEmailTarget.id ? { ...u, email: editEmail, is_admin: editEmailTarget.is_admin, is_active: editEmailTarget.is_active } : u));
      toast(t("settings.toasts.emailUpdatedTitle"), { description: t("settings.toasts.emailUpdatedDescription") });
      setEditEmailOpen(false);
      setEditEmailTarget(null);
    } catch (err: unknown) {
      setEditEmailError((err as Error).message);
    } finally {
      setEditEmailLoading(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setActionError("");
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/auth/users/${deleteTarget.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        throw new Error(await extractError(res, t("settings.errors.deleteFailed")));
      }
      setUsers(prev => prev.filter(u => u.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: unknown) {
      setActionError((err as Error).message);
    } finally {
      setDeleting(false);
    }
  };

    return (
    <>
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <h1 className="text-2xl font-semibold">{t("settings.title")}</h1>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.appearance.title")}</CardTitle>
            <CardDescription>{t("settings.appearance.description")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <Label>{t("settings.appearance.theme")}</Label>
                <p className="text-sm text-muted-foreground mt-1">
                  {theme === "dark" ? t("settings.appearance.darkActive") : t("settings.appearance.lightActive")}
                </p>
              </div>
              <Button variant="secondary" onClick={toggleTheme}>
                {theme === "dark" ? t("settings.appearance.switchToLight") : t("settings.appearance.switchToDark")}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.timezone.title")}</CardTitle>
            <CardDescription>{t("settings.timezone.description")}</CardDescription>
          </CardHeader>
          <CardContent>
            <Label htmlFor="timezone">{t("settings.timezone.current", { timezone })}</Label>
            <select
              id="timezone"
              aria-label={t("settings.timezone.ariaLabel")}
              value={timezone}
              onChange={e => setTimezone(e.target.value)}
              className="mt-2 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              {COMMON_TIMEZONES.map(tz => (
                <option className="bg-background text-foreground" key={tz.value} value={tz.value}>{tz.label}</option>
              ))}
            </select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.dataSource.title")}</CardTitle>
            <CardDescription>{t("settings.dataSource.description")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 mb-1">
              {yfStatus === "loading" && (
                <span className="text-sm">{t("settings.dataSource.checking")}</span>
              )}
              {yfStatus === "ok" && (
                <>
                  <span className="inline-block size-2 rounded-full bg-up" />
                  <span className="text-sm font-medium text-up">{t("settings.dataSource.operational")}</span>
                </>
              )}
              {yfStatus === "error" && (
                <>
                  <span className="inline-block size-2 rounded-full bg-down" />
                  <span className="text-sm font-medium text-down">{t("settings.dataSource.error")}</span>
                </>
              )}
            </div>
            {yfMessage && (
              <p className="text-xs text-muted-foreground mt-1">{yfMessage}</p>
            )}
          </CardContent>
        </Card>

        {isAdmin && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{t("settings.users.title")}</CardTitle>
                <CardDescription>{t("settings.users.description")}</CardDescription>
              </div>
              <Button size="sm" onClick={() => setAddOpen(true)}>{t("settings.users.addUser")}</Button>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {usersLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="size-5 animate-spin text-muted-foreground" />
              </div>
            ) : users.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("settings.users.none")}</p>
            ) : (
              <div className="flex flex-col gap-3">
                {users.map(u => (
                  <div key={u.id} className="flex items-center justify-between rounded-md border p-3">
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <span className="text-sm font-medium truncate">{u.username}</span>
                      <span className="text-xs text-muted-foreground truncate">{u.email}</span>
                      {u.created_at && (
                        <span className="text-xs text-muted-foreground truncate">{t("settings.users.registered", { date: fmtDate(u.created_at) })}</span>
                      )}
                      <span className="text-xs text-muted-foreground truncate">
                        {t("settings.users.lastLogin", { date: u.last_login_at ? fmtDate(u.last_login_at) : t("settings.users.never") })}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditEmail({ id: u.id, email: u.email, is_admin: u.is_admin, is_active: u.is_active })}
                      >
                        <Pencil className="size-3 mr-1" /> {t("settings.users.edit")}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setDeleteTarget({ id: u.id, username: u.username })}
                      >
                        {t("settings.users.delete")}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.about.title")}</CardTitle>
            <CardDescription>{t("settings.about.subtitle")}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <a
              href={RELEASE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:underline"
            >
              {APP_VERSION}
            </a>
            <p className="text-xs text-muted-foreground">
              {t("settings.about.description")}
            </p>
            {releaseNotes ? (
              <details className="mt-2 text-xs">
                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                  {t("settings.about.releaseNotes")}
                </summary>
                <div className="mt-2 max-h-72 overflow-y-auto overflow-x-hidden border-t pt-2 text-xs leading-relaxed text-muted-foreground break-words [&_a]:break-all [&_a]:underline [&_a]:underline-offset-2 [&_h1]:mt-3 [&_h1]:mb-1 [&_h1]:text-sm [&_h1]:font-semibold [&_h1]:text-foreground [&_h2]:mt-3 [&_h2]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:text-foreground [&_h3]:mt-2 [&_h3]:mb-1 [&_h3]:text-xs [&_h3]:font-semibold [&_h3]:text-foreground [&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-4 [&_li]:my-0.5 [&_p]:my-1">
                  <ReactMarkdown
                    components={{
                      a: ({ ...props }) => (
                        <a {...props} target="_blank" rel="noopener noreferrer" />
                      ),
                    }}
                  >
                    {releaseNotes}
                  </ReactMarkdown>
                </div>
              </details>
            ) : (
              <a
                href={RELEASE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:underline"
              >
                {t("settings.about.viewReleaseNotes")}
              </a>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("settings.deleteDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("settings.deleteDialog.description", { username: deleteTarget?.username })}
            </DialogDescription>
          </DialogHeader>
          {actionError && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {actionError}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>{t("settings.deleteDialog.cancel")}</Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting ? t("settings.deleteDialog.deleting") : t("settings.deleteDialog.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={addOpen} onOpenChange={(open) => { if (!open) { setAddOpen(false); setAddError(""); setAddEmail(""); setAddUsername(""); setAddPassword(""); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("settings.addDialog.title")}</DialogTitle>
            <DialogDescription>{t("settings.addDialog.description")}</DialogDescription>
          </DialogHeader>
          <form onSubmit={addUser} className="flex flex-col gap-3">
            {addError && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {addError}
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="add-email">{t("settings.addDialog.email")}</Label>
              <Input
                id="add-email"
                type="email"
                placeholder={t("settings.addDialog.emailPlaceholder")}
                value={addEmail}
                onChange={e => setAddEmail(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="add-username">{t("settings.addDialog.username")}</Label>
              <Input
                id="add-username"
                placeholder={t("settings.addDialog.usernamePlaceholder")}
                value={addUsername}
                onChange={e => setAddUsername(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="add-password">{t("settings.addDialog.password")}</Label>
              <Input
                id="add-password"
                type="password"
                placeholder={t("settings.addDialog.passwordPlaceholder")}
                value={addPassword}
                onChange={e => setAddPassword(e.target.value)}
                required
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAddOpen(false)} disabled={addLoading}>{t("settings.addDialog.cancel")}</Button>
              <Button type="submit" disabled={addLoading}>
                {addLoading ? t("settings.addDialog.creating") : t("settings.addDialog.create")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!resetTarget} onOpenChange={(open) => { if (!open) { setResetTarget(null); setResetResult(null); setResetError(""); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("settings.resetDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("settings.resetDialog.description", { username: resetTarget?.username })}
            </DialogDescription>
          </DialogHeader>
          {resetResult ? (
            <div className="rounded-md border border-green-500/40 bg-green-500/10 px-3 py-3 text-sm">
              <p className="font-medium text-green-600 dark:text-green-400 mb-1">{t("settings.resetDialog.newPassword")}</p>
              <code className="text-base font-mono font-bold break-all">{resetResult}</code>
              <p className="text-xs text-muted-foreground mt-2">{t("settings.resetDialog.copyWarning")}</p>
            </div>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); resetUserPassword(); }} className="flex flex-col gap-3">
              {resetError && (
                <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {resetError}
                </div>
              )}
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setResetTarget(null)} disabled={resetLoading}>{t("settings.resetDialog.cancel")}</Button>
                <Button type="submit" disabled={resetLoading}>
                  {resetLoading ? t("settings.resetDialog.resetting") : t("settings.resetDialog.reset")}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={editEmailOpen} onOpenChange={(open) => { if (!open) { setEditEmailOpen(false); setEditEmailTarget(null); setEditEmailError(""); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("settings.editDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("settings.editDialog.description", { email: editEmailTarget?.email })}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={editUserEmail} className="flex flex-col gap-3">
            {editEmailError && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {editEmailError}
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="edit-email">{t("settings.editDialog.email")}</Label>
              <Input
                id="edit-email"
                type="email"
                placeholder={t("settings.editDialog.emailPlaceholder")}
                value={editEmail}
                onChange={e => setEditEmail(e.target.value)}
                required
              />
            </div>
            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-medium">{t("settings.editDialog.admin")}</span>
                <span className="text-xs text-muted-foreground">{t("settings.editDialog.adminHint")}</span>
              </div>
              <Switch
                checked={editEmailTarget?.is_admin ?? false}
                onCheckedChange={(checked) => setEditEmailTarget(prev => prev ? { ...prev, is_admin: checked } : null)}
              />
            </div>
            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-medium">{t("settings.editDialog.active")}</span>
                <span className="text-xs text-muted-foreground">{t("settings.editDialog.activeHint")}</span>
              </div>
              <Switch
                checked={editEmailTarget?.is_active ?? false}
                onCheckedChange={(checked) => setEditEmailTarget(prev => prev ? { ...prev, is_active: checked } : null)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>{t("settings.editDialog.password")}</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => {
                    if (!editEmailTarget) return;
                    setResetTarget({ id: editEmailTarget.id, username: editEmailTarget.email });
                    setEditEmailOpen(false);
                  }}
                >
                  <Key className="size-3 mr-1" /> {t("settings.editDialog.resetPassword")}
                </Button>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditEmailOpen(false)} disabled={editEmailLoading}>{t("settings.editDialog.cancel")}</Button>
              <Button type="submit" disabled={editEmailLoading}>
                {editEmailLoading ? t("settings.editDialog.saving") : t("settings.editDialog.save")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
