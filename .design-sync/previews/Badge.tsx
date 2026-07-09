import { Badge } from "frontend";

// Dark-first surface: the DS defaults to its dark theme (:root), so previews
// render components on bg-background to match how designs look by default.
const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-wrap items-center gap-2">{children}</div>
);

export const Variants = () => (
  <Surface>
    <Badge>Default</Badge>
    <Badge variant="secondary">Secondary</Badge>
    <Badge variant="destructive">Destructive</Badge>
    <Badge variant="outline">Outline</Badge>
  </Surface>
);

export const StatusLabels = () => (
  <Surface>
    <Badge className="bg-up text-up-foreground border-transparent">Bullish</Badge>
    <Badge className="bg-down text-down-foreground border-transparent">Bearish</Badge>
    <Badge variant="secondary">Neutral</Badge>
    <Badge variant="outline">Watchlist</Badge>
  </Surface>
);
