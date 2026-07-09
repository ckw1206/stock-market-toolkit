import { Toggle } from "frontend";
import { Star, Bell, TrendingUp } from "lucide-react";

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-wrap items-center gap-3">{children}</div>
);

export const States = () => (
  <Surface>
    <Toggle>Off</Toggle>
    <Toggle defaultPressed>On</Toggle>
    <Toggle variant="outline">Outline</Toggle>
    <Toggle variant="outline" defaultPressed>Outline on</Toggle>
    <Toggle disabled>Disabled</Toggle>
  </Surface>
);

export const IconToggles = () => (
  <Surface>
    <Toggle aria-label="Watch" size="sm"><Star /></Toggle>
    <Toggle aria-label="Alerts" size="sm" defaultPressed><Bell /></Toggle>
    <Toggle aria-label="Trend" variant="outline"><TrendingUp /></Toggle>
  </Surface>
);
