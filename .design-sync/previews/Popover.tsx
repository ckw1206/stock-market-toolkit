import {
  Popover, PopoverTrigger, PopoverContent, Button, Label, Input,
} from "frontend";

export const Open = () => (
  <div className="bg-background text-foreground p-6" style={{ minHeight: 260 }}>
    <Popover defaultOpen>
      <PopoverTrigger asChild>
        <Button variant="outline">Alert settings</Button>
      </PopoverTrigger>
      <PopoverContent className="w-72" align="start">
        <div className="grid gap-3">
          <div className="space-y-0.5">
            <h4 className="text-sm font-medium">Price alert</h4>
            <p className="text-xs text-muted-foreground">Trigger when AAPL crosses your target.</p>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="above">Above</Label>
            <Input id="above" defaultValue="245.00" className="font-mono" />
          </div>
        </div>
      </PopoverContent>
    </Popover>
  </div>
);
