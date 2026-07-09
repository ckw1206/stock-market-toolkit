import { Label, Input, Switch } from "frontend";

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-col gap-4 max-w-xs">{children}</div>
);

export const WithInput = () => (
  <Surface>
    <div className="grid gap-1.5">
      <Label htmlFor="target">Target price</Label>
      <Input id="target" defaultValue="245.00" className="font-mono" />
    </div>
  </Surface>
);

export const WithControl = () => (
  <Surface>
    <div className="flex items-center gap-2">
      <Switch id="alerts" defaultChecked />
      <Label htmlFor="alerts">Enable price alerts</Label>
    </div>
  </Surface>
);
