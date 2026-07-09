import { Input, Label } from "frontend";

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-col gap-3 max-w-xs">{children}</div>
);

export const Default = () => (
  <Surface>
    <Input placeholder="Search ticker…" />
    <Input defaultValue="AAPL" />
    <Input type="number" defaultValue="245.00" className="font-mono" />
  </Surface>
);

export const WithLabel = () => (
  <Surface>
    <div className="grid gap-1.5">
      <Label htmlFor="sym">Symbol</Label>
      <Input id="sym" placeholder="e.g. TSLA" />
    </div>
  </Surface>
);

export const Disabled = () => (
  <Surface>
    <Input disabled placeholder="Disabled" />
    <Input disabled defaultValue="Read only" />
  </Surface>
);
