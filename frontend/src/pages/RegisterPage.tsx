import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const API = import.meta.env.VITE_API_URL || "";

function BrandMark() {
  return (
    <svg width="22" height="22" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect width="32" height="32" rx="6" fill="#0f172a" />
      <polyline points="4,22 10,14 16,18 22,8 28,12" stroke="#3b82f6" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="28" cy="12" r="2" fill="#22c55e" />
    </svg>
  );
}

/* ─── Invite-token registration form ─── */
function InviteRegisterForm({ token }: { token: string }) {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError(t("register.errors.passwordTooShort"));
      return;
    }
    setLoading(true);
    try {
      await register(email, username, password, token);
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("register.errors.failed");
      setError(Array.isArray(msg) ? msg.map((m: { msg: string }) => m.msg).join(", ") : msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CardContent className="flex flex-col gap-4">
      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}{" "}
          <Link to="/register" className="underline underline-offset-4">{t("register.requestFallback")}</Link>
        </div>
      )}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">{t("register.email")}</Label>
          <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required autoFocus />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="username">{t("register.username")}</Label>
          <Input id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="traderjoe" required minLength={3} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password">{t("register.password")}</Label>
          <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t("register.passwordPlaceholder")} required minLength={8} />
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? t("register.submitting") : t("register.submit")}
        </Button>
      </form>
      <p className="text-center text-sm text-muted-foreground">
        {t("register.haveAccount")}{" "}
        <Link to="/login" className="text-primary underline-offset-4 hover:underline">{t("register.signIn")}</Link>
      </p>
    </CardContent>
  );
}

/* ─── Request-an-account form (no invite token) ─── */
function RequestAccountForm() {
  const [email, setEmail] = useState("");
  const [note, setNote] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(API + "/api/auth/request-account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, note: note || null }),
      });
      if (!res.ok) throw new Error();
      setSubmitted(true);
    } catch {
      setError(t("register.request.failed"));
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <CardContent className="flex flex-col gap-4 text-center">
        <p className="text-sm">{t("register.request.received")}</p>
        <Link to="/login" className="text-sm text-primary underline-offset-4 hover:underline">{t("register.signIn")}</Link>
      </CardContent>
    );
  }

  return (
    <CardContent className="flex flex-col gap-4">
      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="req-email">{t("register.email")}</Label>
          <Input id="req-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required autoFocus />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="req-note">{t("register.request.noteLabel")}</Label>
          <textarea id="req-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder={t("register.request.notePlaceholder")} maxLength={1000} rows={3} className="flex min-h-16 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs" />
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? t("register.request.submitting") : t("register.request.submit")}
        </Button>
      </form>
      <p className="text-center text-sm text-muted-foreground">
        {t("register.haveAccount")}{" "}
        <Link to="/login" className="text-primary underline-offset-4 hover:underline">{t("register.signIn")}</Link>
      </p>
    </CardContent>
  );
}

export default function RegisterPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const { t } = useTranslation();

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-10">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="flex items-center gap-2 font-semibold">
            <BrandMark /> Stock Toolkit
          </div>
          <CardTitle className="text-xl">
            {token ? t("register.title") : t("register.request.title")}
          </CardTitle>
          <CardDescription>
            {token ? t("register.subtitle") : t("register.request.subtitle")}
          </CardDescription>
        </CardHeader>
        {token ? <InviteRegisterForm token={token} /> : <RequestAccountForm />}
      </Card>
    </div>
  );
}