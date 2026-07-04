import { useState, useEffect, useCallback, useMemo } from "react";
import {
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  updateWatchlistItem,
  type WatchlistItem,
} from "../api/watchlistApi";
import { useAuth } from "./useAuth";

export function useWatchlist() {
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!isAuthenticated) {
      setItems([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await getWatchlist();
      setItems(data);
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Failed to load watchlist"
      );
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    (async () => {
      await refresh();
    })();
  }, [refresh]);

  // Memoize so the reference is stable across renders that don't change
  // `items`. Consumers use `symbols` as a useEffect dependency; a fresh array
  // every render would re-run those effects on every render (and can spin into
  // an infinite update loop). See SignalsPage.
  const symbols: string[] = useMemo(() => items.map((i) => i.symbol), [items]);

  const add = async (symbol: string) => {
    const upper = symbol.toUpperCase();
    if (items.some((i) => i.symbol === upper)) return;
    const item = await addToWatchlist(upper);
    setItems((prev) => [item, ...prev]);
    return item;
  };

  const remove = async (symbol: string) => {
    const upper = symbol.toUpperCase();
    await removeFromWatchlist(upper);
    setItems((prev) => prev.filter((i) => i.symbol !== upper));
  };

  const isWatched = (symbol: string): boolean =>
    items.some((i) => i.symbol === symbol.toUpperCase());

  const update = async (symbol: string, data: { note?: string; tags?: string[] }) => {
    const upper = symbol.toUpperCase();
    const updated = await updateWatchlistItem(upper, data);
    setItems((prev) => prev.map((i) => (i.symbol === upper ? updated : i)));
    return updated;
  };

  return { items, symbols, loading, error, refresh, add, remove, update, isWatched };
}
