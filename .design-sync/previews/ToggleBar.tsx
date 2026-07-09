import { ToggleBar, MultiToggleBar } from "frontend";

const noop = () => {};

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-col gap-4">{children}</div>
);

const ranges = [
  { label: "1D", value: "1d" }, { label: "1W", value: "1w" },
  { label: "1M", value: "1m" }, { label: "1Y", value: "1y" },
];

const indicators = [
  { label: "SMA", value: "sma" }, { label: "EMA", value: "ema" },
  { label: "RSI", value: "rsi" }, { label: "MACD", value: "macd" },
];

export const SingleSelect = () => (
  <Surface>
    <ToggleBar options={ranges} value="1w" onChange={noop} ariaLabel="Time range" />
  </Surface>
);

export const MultiSelect = () => (
  <Surface>
    <MultiToggleBar options={indicators} value={["sma", "rsi"]} onChange={noop} ariaLabel="Indicators" />
  </Surface>
);
