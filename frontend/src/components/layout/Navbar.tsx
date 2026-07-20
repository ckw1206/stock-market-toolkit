import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Sun, Moon, Menu, Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { APP_VERSION } from "@/lib/version";
import { toast } from "@/components/ui/sonner";

const NAV_ITEMS = [
  { to: "/", labelKey: "nav.dashboard", end: true },
  { to: "/signals", labelKey: "nav.signals", end: false },
  { to: "/screener", labelKey: "nav.screener", end: false },
  { to: "/portfolio", labelKey: "nav.portfolio", end: false },
  { to: "/holdings", labelKey: "nav.holdings", end: false },
  { to: "/compare", labelKey: "nav.compare", end: false },
  { to: "/alerts", labelKey: "nav.alerts", end: false },
  { to: "/settings", labelKey: "nav.settings", end: false },
];

export default function Navbar() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changePasswordError, setChangePasswordError] = useState("");
  const [changePasswordLoading, setChangePasswordLoading] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setChangePasswordError("");

    if (newPassword.length < 8) {
      setChangePasswordError(t("common.password.errorMinLength"));
      return;
    }

    if (newPassword !== confirmPassword) {
      setChangePasswordError(t("common.password.errorMismatch"));
      return;
    }

    if (!user) return;

    setChangePasswordLoading(true);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/auth/users/${user.id}/change-password`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });

      if (!res.ok) {
        const d = await res.json();
        throw new Error(typeof d.detail === "string" ? d.detail : t("common.password.errorFailed"));
      }

      toast(t("common.password.changed"), { description: t("common.password.changedDescription") });
      setChangePasswordOpen(false);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("common.password.errorFailed");
      setChangePasswordError(msg);
      toast(t("common.states.error"), { description: msg });
    } finally {
      setChangePasswordLoading(false);
    }
  };

  return (
    <>
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-[1440px] items-center gap-2 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <svg width="24" height="24" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <rect width="32" height="32" rx="6" fill="#0f172a" />
            <polyline points="4,22 10,14 16,18 22,8 28,12" stroke="#3b82f6" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="28" cy="12" r="2" fill="#22c55e" />
          </svg>
          <span className="hidden sm:inline">Stock Toolkit</span>
        </Link>
        <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">{APP_VERSION}</span>

        <nav className="ml-2 hidden items-center gap-1 md:flex">
          {NAV_ITEMS.map(({ to, labelKey, end }) => (
            <NavLink key={to} to={to} end={end}>
              {({ isActive }) => (
                <span
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  )}
                >
                  {t(labelKey)}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label={t("common.theme.toggle")}>
                  {theme === "dark" ? <Sun /> : <Moon />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{theme === "dark" ? t("common.theme.switchToLight") : t("common.theme.switchToDark")}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => i18n.changeLanguage(i18n.language.startsWith("en") ? "zh-TW" : "en")}
                  aria-label="Switch language"
                >
                  <Languages />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{i18n.language.startsWith("en") ? t("nav.switchToChinese") : t("nav.switchToEnglish")}</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm">{user.username}</Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{user.username}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {user?.is_admin && (
                  <DropdownMenuItem onClick={() => navigate("/admin/logs")}>
                    {t("common.menu.logViewer")}
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={() => navigate("/admin/invites")}>
                  {t("common.menu.invitations")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setChangePasswordOpen(true)}>
                  {t("common.actions.changePassword")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => { logout(); navigate("/login"); }}>
                  {t("common.actions.logOut")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          <div className="md:hidden">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" aria-label={t("common.menu.openNavigation")}>
                  <Menu />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {NAV_ITEMS.map(({ to, labelKey, end }) => (
                  <DropdownMenuItem key={to} asChild>
                    <NavLink to={to} end={end}>{t(labelKey)}</NavLink>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </header>

    <Dialog open={changePasswordOpen} onOpenChange={(open) => { if (!open) { setChangePasswordOpen(false); setChangePasswordError(""); setCurrentPassword(""); setNewPassword(""); setConfirmPassword(""); } }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("common.actions.changePassword")}</DialogTitle>
          <DialogDescription>
            {t("common.password.dialogDescription")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleChangePassword} className="flex flex-col gap-3">
          {changePasswordError && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {changePasswordError}
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="current-password">{t("common.password.current")}</Label>
            <Input
              id="current-password"
              type="password"
              placeholder={t("common.password.currentPlaceholder")}
              value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-password">{t("common.password.new")}</Label>
            <Input
              id="new-password"
              type="password"
              placeholder={t("common.password.newPlaceholder")}
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="confirm-password">{t("common.password.confirm")}</Label>
            <Input
              id="confirm-password"
              type="password"
              placeholder={t("common.password.confirmPlaceholder")}
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setChangePasswordOpen(false)} disabled={changePasswordLoading}>{t("common.actions.cancel")}</Button>
            <Button type="submit" disabled={changePasswordLoading}>
              {changePasswordLoading ? t("common.actions.saving") : t("common.actions.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
    </>
  );
}
