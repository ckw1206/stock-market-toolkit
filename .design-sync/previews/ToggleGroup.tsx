import { ToggleGroup, ToggleGroupItem } from "frontend";

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-col gap-4">{children}</div>
);

export const Single = () => (
  <Surface>
    <ToggleGroup type="single" defaultValue="1d" variant="outline" size="sm">
      <ToggleGroupItem value="1d">1D</ToggleGroupItem>
      <ToggleGroupItem value="1w">1W</ToggleGroupItem>
      <ToggleGroupItem value="1m">1M</ToggleGroupItem>
      <ToggleGroupItem value="1y">1Y</ToggleGroupItem>
    </ToggleGroup>
  </Surface>
);

export const Multiple = () => (
  <Surface>
    <ToggleGroup type="multiple" defaultValue={["sma", "rsi"]} variant="outline" size="sm">
      <ToggleGroupItem value="sma">SMA</ToggleGroupItem>
      <ToggleGroupItem value="ema">EMA</ToggleGroupItem>
      <ToggleGroupItem value="rsi">RSI</ToggleGroupItem>
      <ToggleGroupItem value="macd">MACD</ToggleGroupItem>
    </ToggleGroup>
  </Surface>
);
