import axios from "axios";
import { API, authHeaders } from "./stockApi";
import type { Currency, TxnType } from "@/lib/holdings";

export interface HoldingsTxn {
  id: number;
  type: TxnType;
  trade_date: string;
  symbol: string | null;
  qty: string | null;
  price: string | null;
  amount: string | null;
  fee: string;
  currency: Currency;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface LedgerWarning {
  kind: "negative_position" | "negative_cash" | "mixed_currency";
  trade_date: string;
  transaction_id: number;
  symbol: string | null;
  currency: string | null;
  message: string;
}

export interface Holding {
  symbol: string;
  currency: Currency;
  qty: string;
  avg_cost: string | null;
  price: string | null;
  market_value: string | null;
  unrealized_pnl: string | null;
  realized_pnl: string;
  dividends: string;
}

export interface CurrencyTotals {
  cash: string;
  market_value: string;
  unrealized_pnl: string;
  realized_pnl: string;
  dividends: string;
  market_value_complete: boolean;
}

export interface HoldingsSummary {
  currencies: Record<string, CurrencyTotals>;
  holdings: Holding[];
  warnings: LedgerWarning[];
}

export interface Suggestion {
  symbol: string;
  type: "dividend" | "split";
  ex_date: string;
  shares: string;
  per_share: string | null;
  gross_amount: string | null;
  ratio: string | null;
  currency: Currency;
}

export interface SuggestionsResponse {
  suggestions: Suggestion[];
  degraded: boolean;
  degraded_symbols: string[];
}

export interface TxnPayload {
  type: TxnType;
  trade_date: string;
  symbol?: string | null;
  qty?: string | null;
  price?: string | null;
  amount?: string | null;
  fee?: string;
  currency?: Currency | null;
  note?: string | null;
}

export interface TxnWithWarnings {
  transaction: HoldingsTxn;
  warnings: LedgerWarning[];
}

export async function listHoldingsTxns(
  filters: { symbol?: string; type?: string } = {},
): Promise<HoldingsTxn[]> {
  const params = new URLSearchParams();
  if (filters.symbol) params.set("symbol", filters.symbol);
  if (filters.type) params.set("type", filters.type);
  const qs = params.toString();
  const res = await axios.get(
    `${API}/api/portfolio/transactions${qs ? `?${qs}` : ""}`,
    { headers: authHeaders() },
  );
  return res.data;
}

export async function createHoldingsTxn(payload: TxnPayload): Promise<TxnWithWarnings> {
  const res = await axios.post(`${API}/api/portfolio/transactions`, payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateHoldingsTxn(
  id: number, payload: TxnPayload,
): Promise<TxnWithWarnings> {
  const res = await axios.put(`${API}/api/portfolio/transactions/${id}`, payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function deleteHoldingsTxn(id: number): Promise<{ warnings: LedgerWarning[] }> {
  const res = await axios.delete(`${API}/api/portfolio/transactions/${id}`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function getHoldingsSummary(): Promise<HoldingsSummary> {
  const res = await axios.get(`${API}/api/portfolio/summary`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function getHoldingsSuggestions(): Promise<SuggestionsResponse> {
  const res = await axios.get(`${API}/api/portfolio/suggestions`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function acceptSuggestion(payload: {
  symbol: string;
  type: "dividend" | "split";
  ex_date: string;
  amount?: string;
  ratio?: string;
}): Promise<TxnWithWarnings> {
  const res = await axios.post(`${API}/api/portfolio/suggestions/accept`, payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function dismissSuggestion(payload: {
  symbol: string;
  type: "dividend" | "split";
  ex_date: string;
}): Promise<{ ok: boolean }> {
  const res = await axios.post(`${API}/api/portfolio/suggestions/dismiss`, payload, {
    headers: authHeaders(),
  });
  return res.data;
}