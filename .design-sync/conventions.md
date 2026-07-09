# Stock Toolkit UI — how to build with this design system

A React + Tailwind (shadcn/ui) library for a stock-analysis app. Style with
Tailwind utility classes bound to CSS-variable tokens. **Read the compiled
stylesheet (`_ds/<folder>/styles.css` and its `@import`s) and each component's
`<Name>.d.ts` / `<Name>.prompt.md` before styling** — they are the source of truth.

## Theme: dark-first

The default theme (`:root`) is **dark** (deep navy surfaces). A light theme is
opt-in via a `data-theme="light"` attribute on an ancestor. Build on the dark
default unless asked otherwise; put page content on `bg-background text-foreground`.
Preflight is disabled, so rely on the token utilities below rather than browser
defaults.

## Styling idiom: token utility classes

Never hardcode hex colors — use these families (each has `bg-*`, most have a
paired `*-foreground` for text on that surface):

| Token | Use |
|---|---|
| `background` / `foreground` | page surface + primary text |
| `card` / `card-foreground` | raised card surface |
| `popover` / `popover-foreground` | menus, dropdowns, tooltips |
| `primary` / `primary-foreground` | primary actions, accents (brand blue) |
| `secondary` / `secondary-foreground` | secondary buttons, subtle fills |
| `muted` / `muted-foreground` | muted fills + secondary text |
| `accent` / `accent-foreground` | hover/active surfaces |
| `destructive` / `destructive-foreground` | errors, destructive actions |
| `border`, `input` | borders + form field borders |

**Domain (finance) tokens** — use these for market direction, not raw green/red:
`text-up` / `bg-up` (gains, positive), `text-down` / `bg-down` (losses, negative),
`text-neutral` (flat). Example: `<span className="text-up">+1.49%</span>`.

**Type**: `font-sans` = Inter (default), `font-mono` = JetBrains Mono. Put all
numeric/financial figures in `font-mono tabular-nums` so columns align (prices,
percentages, volume). Radius scales from `--radius` via `rounded-md`/`rounded-lg`/`rounded-xl`.

## Providers

Wrap any tree that uses `Tooltip` (or `WatchlistButton`) in `<TooltipProvider>`.
Several components (`SignalCard`, `SymbolSearch`, `CacheBadge`, `WatchlistButton`)
call `useTranslation` from react-i18next — in a real app, initialize i18next at
the root. `WatchlistButton` also reads auth + watchlist context and renders
nothing until the user is authenticated.

## Example

```tsx
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from "…";

<div className="bg-background text-foreground p-6">
  <Card className="max-w-sm">
    <CardHeader className="flex-row items-start justify-between space-y-0">
      <CardTitle>AAPL · Apple Inc.</CardTitle>
      <Badge className="bg-up text-up-foreground border-transparent">Bullish</Badge>
    </CardHeader>
    <CardContent>
      <div className="font-mono text-2xl font-semibold tabular-nums">$232.14</div>
      <div className="font-mono text-sm text-up tabular-nums">+3.42 (+1.49%)</div>
      <Button size="sm" className="mt-3">Analyze</Button>
    </CardContent>
  </Card>
</div>
```
