import axios from "axios";

const API = import.meta.env.VITE_API_URL || "";

function getToken(): string | null {
  return localStorage.getItem("access_token");
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Alert Types ───
export interface AlertCondition {
  id: number;
  alert_id: number;
  metric: "price" | "rsi" | "macd_hist" | "signal" | "pct_change";
  operator: "gt" | "lt" | "crosses_above" | "eq";
  value: number;
}

export interface Alert {
  id: number;
  user_id: string;
  symbol: string;
  symbol_name?: string;
  condition_type: string;
  threshold: number;
  period: string;
  enabled: boolean;
  combinator?: "all" | "any";
  conditions: AlertCondition[];
  cooldown_until: string | null;
  created_at: string;
}

export interface TriggeredAlert {
  id: number;
  alert_id: number | null;
  user_id: string;
  symbol: string;
  symbol_name?: string;
  condition_type: string;
  trigger_price: number;
  threshold_value: number;
  triggered_at: string;
  notified: boolean;
  read: boolean;
}

export interface NotificationSettings {
  user_id: string;
  discord_webhook_url: string | null;
  email_address: string | null;
  email_enabled: boolean;
  email_subject: string | null;
  email_body: string | null;
  discord_enabled: boolean;
  default_period: string;
  timezone: string;
  updated_at: string | null;
  // Per-user SMTP fields
  smtp_host?: string | null;
  smtp_port?: number | null;
  smtp_use_tls?: boolean | null;
  smtp_username?: string | null;
  smtp_password?: string | null; // write-only — never returned as plain text
  smtp_from_address?: string | null;
  smtp_reply_to?: string | null;
  smtp_password_set?: boolean; // response-only — never sent to backend
}

export interface AlertConditionCreate {
  metric: "price" | "rsi" | "macd_hist" | "signal" | "pct_change" | "rvol";
  operator: "gt" | "lt" | "crosses_above" | "eq";
  value: number;
}

export interface AlertCreate {
  symbol: string;
  symbol_name?: string;
  condition_type?: "above" | "below" | "pct_change_up" | "pct_change_down";
  threshold?: number;
  period?: string;
  combinator?: "all" | "any";
  conditions?: AlertConditionCreate[];
}

export interface AlertUpdate {
  symbol?: string;
  symbol_name?: string;
  condition_type?: string;
  threshold?: number;
  period?: string;
  enabled?: boolean;
  combinator?: "all" | "any";
  conditions?: AlertConditionCreate[];
}

// ─── Alert API Functions ───
export async function createAlert(data: AlertCreate): Promise<Alert> {
  const res = await axios.post(`${API}/api/alerts`, data, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function getAlerts(): Promise<Alert[]> {
  const res = await axios.get(`${API}/api/alerts`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateAlert(alertId: number, data: AlertUpdate): Promise<Alert> {
  const res = await axios.patch(`${API}/api/alerts/${alertId}`, data, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function deleteAlert(alertId: number): Promise<void> {
  await axios.delete(`${API}/api/alerts/${alertId}`, {
    headers: authHeaders(),
  });
}

export async function getTriggeredAlerts(unreadOnly = false): Promise<TriggeredAlert[]> {
  const res = await axios.get(`${API}/api/alerts/triggered`, {
    params: { unread_only: unreadOnly },
    headers: authHeaders(),
  });
  return res.data;
}

export async function markTriggeredAlertRead(alertId: number): Promise<TriggeredAlert> {
  const res = await axios.patch(`${API}/api/alerts/triggered/${alertId}/read`, {}, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function getNotificationSettings(): Promise<NotificationSettings> {
  const res = await axios.get(`${API}/api/alerts/settings`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateNotificationSettings(data: Partial<NotificationSettings>): Promise<NotificationSettings> {
  const res = await axios.put(`${API}/api/alerts/settings`, data, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function testDiscordWebhook(webhookUrl: string): Promise<{ ok: boolean }> {
  const res = await axios.post(
    `${API}/api/alerts/notifications/test-discord`,
    { webhook_url: webhookUrl },
    { headers: authHeaders() }
  );
  return res.data;
}

export async function testSmtpSettings(to?: string): Promise<{ success: boolean; message: string }> {
  const res = await axios.post(
    `${API}/api/alerts/settings/smtp/test`,
    to ? { to } : {},
    { headers: authHeaders() }
  );
  return res.data;
}