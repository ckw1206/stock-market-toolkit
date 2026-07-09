import { ChartCard, Badge } from "frontend";

// A lightweight inline sparkline stands in for a real chart child so the card
// composition (header, toolbar, body) reads as it would in the app.
const Sparkline = ({ color }: { color: string }) => (
  <svg viewBox="0 0 200 60" className="h-24 w-full" preserveAspectRatio="none">
    <polyline
      points="0,45 20,40 40,42 60,30 80,34 100,22 120,26 140,14 160,18 180,8 200,10"
      fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    />
  </svg>
);

export const Default = () => (
  <div className="bg-background text-foreground p-6">
    <ChartCard
      title="AAPL price"
      subtitle="1D · NASDAQ"
      toolbar={<Badge className="bg-up text-up-foreground border-transparent">+1.49%</Badge>}
      className="w-[320px]"
    >
      <Sparkline color="hsl(var(--up))" />
    </ChartCard>
  </div>
);

export const NoHeader = () => (
  <div className="bg-background text-foreground p-6">
    <ChartCard className="w-[320px]">
      <Sparkline color="hsl(var(--primary))" />
    </ChartCard>
  </div>
);
