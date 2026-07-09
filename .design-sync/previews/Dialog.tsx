import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
  DialogFooter, Button, Input, Label,
} from "frontend";

export const Open = () => (
  <div className="bg-background text-foreground" style={{ minHeight: 380 }}>
    <Dialog defaultOpen modal={false}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create price alert</DialogTitle>
          <DialogDescription>
            Notify me when AAPL crosses the target price.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 py-2">
          <div className="grid gap-1.5">
            <Label htmlFor="target">Target price</Label>
            <Input id="target" defaultValue="245.00" className="font-mono" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline">Cancel</Button>
          <Button>Create alert</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
);
