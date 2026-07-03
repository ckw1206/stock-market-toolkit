import type { LayoutItem } from "react-grid-layout";

const KEY = "stock-toolkit-dash-layout";
export const LAYOUT_VERSION = 1;

/** Optional data-driven cards, in static-grid order. Rendered only when their
 * data is present, so they get a layout entry only when listed in `extras`. */
export const OPTIONAL_CARDS = ["fundamentals", "dividends", "news", "topsignals"] as const;

/**
 * Default grid placement for the editable dashboard, mirroring the static grid
 * order. `active` holds the toggled indicators (rsi/macd); `extras` holds the
 * optional data cards (fundamentals/dividends/news) that currently have data.
 *
 * Every rendered child MUST have a layout entry — react-grid-layout drops
 * children whose key is missing from the layout — so a card absent here will
 * not render in edit mode at all.
 */
export function defaultLayout(active: Set<string>, extras: Set<string> = new Set()): LayoutItem[] {
  let y = 0;
  const layout: LayoutItem[] = [];
  layout.push({ i: "price", x: 0, y, w: 12, h: 3, minW: 6 });
  y += 3;
  if (active.has("rsi")) layout.push({ i: "rsi", x: 0, y, w: 6, h: 1, minW: 4 });
  if (active.has("macd")) layout.push({ i: "macd", x: active.has("rsi") ? 6 : 0, y, w: 6, h: 1, minW: 4 });
  if (active.has("rsi") || active.has("macd")) y += 1;
  layout.push({ i: "info", x: 0, y, w: 4, h: 10, minW: 3 });
  layout.push({ i: "table", x: 4, y, w: 8, h: 6, minW: 4 });
  // Optional cards flow in a row beneath the info/table block. Start below the
  // taller of the two (info, h10) so they can never collide with it.
  y += 10;
  let x = 0;
  for (const id of OPTIONAL_CARDS) {
    if (!extras.has(id)) continue;
    layout.push({ i: id, x, y, w: 4, h: 6, minW: 3 });
    x += 4;
    if (x >= 12) { x = 0; y += 6; }
  }
  return layout;
}

/**
 * Reconcile a saved layout with the currently-visible widgets. When the saved
 * widget set matches exactly, the saved layout is honored verbatim. When it
 * differs (e.g. an indicator was toggled), user sizes are preserved but each
 * widget's position is taken from the collision-free default — so a stale saved
 * position can never seed an overlap.
 */
export function reconcileLayout(
  stored: LayoutItem[],
  active: Set<string>,
  extras: Set<string> = new Set(),
): LayoutItem[] {
  const base = defaultLayout(active, extras);
  const storedIds = new Set(stored.map((l) => l.i));
  const sameSet = base.length === stored.length && base.every((b) => storedIds.has(b.i));
  return base.map((b) => {
    const s = stored.find((l) => l.i === b.i);
    if (sameSet && s) return s;
    return s ? { ...b, w: s.w, h: s.h } : b;
  });
}

export function saveLayout(items: readonly LayoutItem[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ version: LAYOUT_VERSION, items }));
  } catch {
    /* ignore quota / serialization errors */
  }
}

export function loadLayout(): LayoutItem[] | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { version?: number; items?: LayoutItem[] };
    if (parsed.version !== LAYOUT_VERSION || !Array.isArray(parsed.items)) return null;
    return parsed.items;
  } catch {
    return null;
  }
}
