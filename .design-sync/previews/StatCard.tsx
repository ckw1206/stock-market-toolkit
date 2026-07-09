import { StatCard } from "frontend";

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6">{children}</div>
);

export const Grid = () => (
  <Surface>
    <div className="grid grid-cols-2 gap-3 max-w-md sm:grid-cols-4">
      <StatCard label="Last" value="$232.14" delta="+1.49%" tone="up" />
      <StatCard label="Day range" value="$228 – $233" tone="neutral" />
      <StatCard label="RSI (14)" value="61.2" delta="+4.1" tone="up" />
      <StatCard label="Volume" value="48.2M" delta="-12%" tone="down" />
    </div>
  </Surface>
);

export const Tones = () => (
  <Surface>
    <div className="flex gap-3">
      <StatCard label="Gain" value="+$4.20" delta="+1.8%" tone="up" />
      <StatCard label="Loss" value="-$2.10" delta="-0.9%" tone="down" />
      <StatCard label="Flat" value="$0.00" delta="0.0%" tone="neutral" />
    </div>
  </Surface>
);
