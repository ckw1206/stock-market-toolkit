import { SymbolSearch } from "frontend";

const noop = () => {};

// Live search is interaction + network driven; the representative static state
// is the closed trigger. `value` renders the selected symbol; without it the
// trigger shows the (i18n) placeholder prompt.
export const Selected = () => (
  <div className="bg-background text-foreground p-6">
    <SymbolSearch value="AAPL" onSearch={noop} />
  </div>
);

export const Empty = () => (
  <div className="bg-background text-foreground p-6">
    <SymbolSearch onSearch={noop} />
  </div>
);
