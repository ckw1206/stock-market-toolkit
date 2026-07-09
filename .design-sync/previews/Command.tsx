import {
  Command, CommandInput, CommandList, CommandEmpty, CommandGroup,
  CommandItem, CommandSeparator, CommandShortcut,
} from "frontend";
import { Search, Star, TrendingUp } from "lucide-react";

export const Palette = () => (
  <div className="bg-background text-foreground p-6">
    <Command className="w-80 rounded-lg border shadow-md">
      <CommandInput placeholder="Search tickers or actions…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Tickers">
          <CommandItem><TrendingUp className="mr-2 size-4" /> AAPL · Apple Inc.</CommandItem>
          <CommandItem><TrendingUp className="mr-2 size-4" /> MSFT · Microsoft</CommandItem>
          <CommandItem><TrendingUp className="mr-2 size-4" /> NVDA · NVIDIA</CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Actions">
          <CommandItem><Search className="mr-2 size-4" /> Open screener <CommandShortcut>⌘K</CommandShortcut></CommandItem>
          <CommandItem><Star className="mr-2 size-4" /> View watchlist</CommandItem>
        </CommandGroup>
      </CommandList>
    </Command>
  </div>
);
