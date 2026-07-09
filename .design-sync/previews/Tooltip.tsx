import { Tooltip, TooltipTrigger, TooltipContent, Button } from "frontend";
import { Info } from "lucide-react";

export const Open = () => (
  <div className="bg-background text-foreground p-6 flex justify-center" style={{ minHeight: 120 }}>
    <Tooltip defaultOpen>
      <TooltipTrigger asChild>
        <Button variant="outline" size="icon" aria-label="Info"><Info /></Button>
      </TooltipTrigger>
      <TooltipContent>Relative volume vs 30-day average</TooltipContent>
    </Tooltip>
  </div>
);
