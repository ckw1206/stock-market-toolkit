import axios from "axios";

const API = import.meta.env.VITE_API_URL || "";

function getToken(): string | null {
  return localStorage.getItem("access_token");
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface WatchlistItem {
  id: number;
  user_id: string;
  symbol: string;
  note: string | null;
  tags: string[];
  created_at: string;
}

export async function getWatchlist(): Promise<WatchlistItem[]> {
  const res = await axios.get(`${API}/api/watchlist`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function addToWatchlist(symbol: string): Promise<WatchlistItem> {
  const res = await axios.post(
    `${API}/api/watchlist`,
    { symbol },
    { headers: authHeaders() }
  );
  return res.data;
}

export async function removeFromWatchlist(symbol: string): Promise<void> {
  await axios.delete(`${API}/api/watchlist/${symbol}`, {
    headers: authHeaders(),
  });
}

export async function updateWatchlistItem(
  symbol: string,
  data: { note?: string; tags?: string[] }
): Promise<WatchlistItem> {
  const res = await axios.patch(`${API}/api/watchlist/${symbol}`, data, {
    headers: authHeaders(),
  });
  return res.data;
}
