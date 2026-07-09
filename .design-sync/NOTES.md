# design-sync notes — Stock Toolkit UI

Repo-specific gotchas for `/design-sync`. The DS is the app's `frontend/` component
library (React 19 + Vite + Tailwind + shadcn/ui). Shape: **package**, synth-entry
(the app has no library `dist/`/`.d.ts` build).

## Build setup

- **Custom barrel entry**: `frontend/.ds-entry.tsx` (committed) named-exports the 25
  scoped components. It exists because (a) the app ships no typed library entry, and
  (b) `export *` from src skips **default** exports — several scoped components
  (`StatCard`, `ChartCard`, `SignalCard`, `SymbolSearch`, `CacheBadge`,
  `WatchlistButton`) are `export default`, so they're re-exported as named here.
  Passed via `--entry ./frontend/.ds-entry.tsx`. `globalName` = `StockUI`.
- **i18n init**: the barrel does `import "./src/i18n"` (relative, not `@/i18n` —
  esbuild's paths plugin doesn't resolve a directory index for the alias). This runs
  i18next's synchronous init inside the bundle so `useTranslation` components render
  real English copy instead of raw keys. Without it, CacheBadge/SignalCard/SymbolSearch
  show i18n keys.
- **CSS is compiled**: components use Tailwind utility classes, so the raw
  `src/index.css` (`@tailwind` directives) is useless as `cssEntry`. `.ds-compiled.css`
  is the **compiled** stylesheet (all utilities + token vars + a Google-Fonts `@import`
  prepended). It is **gitignored** — regenerate before every re-sync:
  ```
  cd frontend
  npx tailwindcss -i src/index.css -o .ds-compiled.tw.css --minify
  printf "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');\n" > .ds-compiled.css
  cat .ds-compiled.tw.css >> .ds-compiled.css && rm .ds-compiled.tw.css
  ```
- `cfg.tsconfig` = `tsconfig.app.json` (has `@/* → ./src/*` paths for esbuild).
- Build/validate/capture: run from repo root; `--node-modules ./frontend/node_modules`.
  playwright cache build 1228 matches latest `playwright` — no browser download.

## Scope + floor cards

- Scoped: all 18 `ui/` primitives + 6 reusable `common/` + `SignalCard`. Excluded:
  `dashboard/` and `layout/` (page scaffolding, not reusable DS parts).
- **Floor cards (intentional, not failures)**:
  - `Toaster` (sonner) — a portal toaster with nothing to show statically.
  - `WatchlistButton` — `return null` unless `useAuth().isAuthenticated`; needs auth +
    watchlist context that isn't feasible to mock. Author a preview only if those
    providers get wired into `cfg.provider`.

## Overlays

Render open state with `defaultOpen` (Select/Dialog/DropdownMenu/Popover) — portal
content captures fine in grid mode, no `cardMode` override needed. Dialog uses
`modal={false}` so the backdrop doesn't dominate the card. Command renders inline.

## Preview convention

All previews wrap content in `bg-background text-foreground` — the DS is **dark-first**
(`:root` = dark), so this shows components on their real default surface (the preview
harness page is white).

## Known render warns (expected — not new)

- `[FONT_REMOTE] "Inter", "JetBrains Mono"` — fonts load via a Google Fonts `@import`
  in `styles.css`; they render at runtime. No local `@font-face` shipped by design.
- `tokens: 1 missing, below threshold` — non-blocking.

## Re-sync risks (watch-list)

- **`.ds-compiled.css` is gitignored** → MUST recompile (command above) before re-sync,
  or the upload ships stale/empty CSS. If Tailwind config or new utility classes change,
  the recompile picks them up (content scan covers `src/**`).
- **`.ds-entry.tsx` is committed but hand-maintained** → if components are added/removed
  in `ui/`/`common/`, update BOTH the barrel and `cfg.componentSrcMap`.
- **i18n keys**: previews assume the English `en.json` keys used by SignalCard/CacheBadge/
  SymbolSearch still exist. If a key is renamed upstream, the preview shows the raw key —
  re-grade those cells.
- **SignalCard preview** inlines a mock `Signal` object shaped to `src/types/index.ts`.
  If the `Signal`/`BacktestStats` type changes, update `.design-sync/previews/SignalCard.tsx`.
- Fonts are network-fetched at capture time; an offline capture will render fallback fonts.
