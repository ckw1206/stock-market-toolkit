import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, Button,
} from "frontend";
import { LineChart, BarChart3, Wallet, X } from "lucide-react";

export const Open = () => (
  <div className="bg-background text-foreground p-6" style={{ minHeight: 260 }}>
    <DropdownMenu defaultOpen>
      <DropdownMenuTrigger asChild>
        <Button variant="outline">AAPL actions</Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-48">
        <DropdownMenuLabel>Apple Inc.</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem><LineChart className="mr-2 size-4" /> View on dashboard</DropdownMenuItem>
        <DropdownMenuItem><BarChart3 className="mr-2 size-4" /> Compare</DropdownMenuItem>
        <DropdownMenuItem><Wallet className="mr-2 size-4" /> Paper trade</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem className="text-destructive"><X className="mr-2 size-4" /> Stop tracking</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
);
