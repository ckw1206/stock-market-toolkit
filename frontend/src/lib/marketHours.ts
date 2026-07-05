/**
 * Market hours utility — mirrors backend/app/services/market_hours.py.
 * Timezone-aware open/closed checks for US and Taiwan equity markets.
 * Uses the Intl.Segmenter-aware Date API (built-in, no external deps).
 */

/** US federal holidays for 2026 — hard-coded (month, day) → name. */
const US_HOLIDAYS_2026: Record<number, string> = {
  101: "New Year's Day",
  119: "Martin Luther King Jr. Day",
  216: "Presidents' Day",
  525: "Memorial Day",
  619: "Juneteenth",
  703: "Independence Day (observed)",
  907: "Labor Day",
  1012: "Columbus Day",
  1111: "Veterans Day",
  1225: "Christmas Day",
};

/**
 * Extract wallclock components (year, month, day, hour, minute, weekday)
 * for a UTC ms timestamp in the given IANA timezone — directly from
 * Intl.DateTimeFormat output, no intermediate Date.getHours() call
 * that would inject the host machine's local timezone.
 */
function getMarketComponents(utcMs: number, timezone: string) {
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    weekday: "short",
  });
  const parts = Object.fromEntries(
    fmt.formatToParts(new Date(utcMs)).map(p => [p.type, p.value]),
  );
  return {
    year: parseInt(parts.year, 10),
    month: parseInt(parts.month, 10),
    day: parseInt(parts.day, 10),
    hour: parseInt(parts.hour, 10),
    minute: parseInt(parts.minute, 10),
    weekday: ["sun", "mon", "tue", "wed", "thu", "fri", "sat"].indexOf(
      (parts.weekday as string).toLowerCase(),
    ),
  };
}

/** Returns true if the given UTC ms timestamp falls on a US market holiday (America/New_York). */
function isUsHoliday(utcMs: number): boolean {
  const { month, day } = getMarketComponents(utcMs, "America/New_York");
  const key = month * 100 + day;
  return key in US_HOLIDAYS_2026;
}

/** Returns true if US equity markets (NYSE/NASDAQ) are open at the given UTC ms timestamp. */
function usMarketOpen(utcMs: number): boolean {
  const { hour, minute, weekday } = getMarketComponents(utcMs, "America/New_York");

  // Weekend
  if (weekday === 0 || weekday === 6) return false;

  // Holiday
  if (isUsHoliday(utcMs)) return false;

  // Time check: 09:30–16:05 ET
  if (hour < 9 || hour > 16) return false;
  if (hour === 9 && minute < 30) return false;
  if (hour === 16 && minute > 5) return false;

  return true;
}

/** Returns true if Taiwan equity markets (TWSE) are open at the given UTC ms timestamp. */
function twMarketOpen(utcMs: number): boolean {
  const { hour, minute, weekday } = getMarketComponents(utcMs, "Asia/Taipei");

  // Weekend
  if (weekday === 0 || weekday === 6) return false;

  // Time check: 09:00–13:35 TPE
  if (hour < 9 || hour > 13) return false;
  if (hour === 9 && minute < 0) return false;
  if (hour === 13 && minute > 35) return false;

  return true;
}

/**
 * Returns true if the symbol's primary exchange is open right now (UTC).
 * Routing:
 *   - Symbols ending in .TW or .TWO  → Taiwan exchange (TWSE)
 *   - All other symbols             → US exchange (NYSE/NASDAQ)
 */
export function isMarketOpen(symbol: string): boolean {
  const sym = symbol.toUpperCase();
  const nowUtcMs = Date.now();
  if (sym.endsWith(".TW") || sym.endsWith(".TWO")) {
    return twMarketOpen(nowUtcMs);
  }
  return usMarketOpen(nowUtcMs);
}

/**
 * Returns "open" | "closed" based on current market state.
 */
export type MarketStatus = "open" | "closed";

export function getMarketStatus(symbol: string): MarketStatus {
  return isMarketOpen(symbol) ? "open" : "closed";
}

/**
 * Returns the UTC ISO string of the next US/Taiwan market open for the given symbol,
 * skipping weekends and US federal holidays.
 * Used for the "Until next market open" snooze option.
 */
export function nextMarketOpenUtc(symbol: string): string {
  const sym = symbol.toUpperCase();
  const isUS = !(sym.endsWith(".TW") || sym.endsWith(".TWO"));

  // Start checking from the current time
  let utcMs = Date.now();

  // Move to the next minute boundary to avoid edge-case precision issues
  utcMs = Math.ceil(utcMs / 60_000) * 60_000;

  // Search up to 7 days ahead (covers a full week + holidays)
  for (let i = 0; i < 7 * 24 * 60; i++) {
    utcMs += 60_000; // advance one minute
    const { weekday, hour, minute } = getMarketComponents(utcMs, isUS ? "America/New_York" : "Asia/Taipei");

    // Weekend check
    if (weekday === 0 || weekday === 6) continue;

    // US market: skip holidays; Taiwan market has no extra holiday list in this util
    if (isUS && isUsHoliday(utcMs)) continue;

    // US market opens at 09:30 ET; Taiwan at 09:00 TPE
    const openHour = isUS ? 9 : 9;
    const openMin = isUS ? 30 : 0;

    if (hour === openHour && minute === openMin) {
      return new Date(utcMs).toISOString();
    }
  }

  // Fallback: 24 hours from now (should never happen for US/Taiwan markets)
  return new Date(Date.now() + 86_400_000).toISOString();
}