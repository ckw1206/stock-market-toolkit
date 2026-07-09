import { Separator } from "frontend";

export const Horizontal = () => (
  <div className="bg-background text-foreground p-6 max-w-xs">
    <div className="text-sm font-medium">Apple Inc.</div>
    <div className="text-xs text-muted-foreground">NASDAQ · AAPL</div>
    <Separator className="my-3" />
    <div className="text-sm text-muted-foreground">Technology · Consumer Electronics</div>
  </div>
);

export const Vertical = () => (
  <div className="bg-background text-foreground p-6">
    <div className="flex h-6 items-center gap-3 text-sm">
      <span>Open</span>
      <Separator orientation="vertical" />
      <span>High</span>
      <Separator orientation="vertical" />
      <span>Low</span>
      <Separator orientation="vertical" />
      <span>Close</span>
    </div>
  </div>
);
