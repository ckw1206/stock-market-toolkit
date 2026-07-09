import { Switch, Label } from "frontend";

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-col gap-4">{children}</div>
);

export const States = () => (
  <Surface>
    <div className="flex items-center gap-2"><Switch defaultChecked /><span className="text-sm">On</span></div>
    <div className="flex items-center gap-2"><Switch /><span className="text-sm">Off</span></div>
    <div className="flex items-center gap-2"><Switch disabled defaultChecked /><span className="text-sm text-muted-foreground">Disabled</span></div>
  </Surface>
);

export const Setting = () => (
  <Surface>
    <div className="flex items-center justify-between gap-6 max-w-xs">
      <Label htmlFor="rt">Real-time quotes</Label>
      <Switch id="rt" defaultChecked />
    </div>
    <div className="flex items-center justify-between gap-6 max-w-xs">
      <Label htmlFor="ah">Extended hours</Label>
      <Switch id="ah" />
    </div>
  </Surface>
);
