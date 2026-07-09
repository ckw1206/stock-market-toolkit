import { Button } from "frontend";
import { TrendingUp, Search } from "lucide-react";

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-wrap items-center gap-3">{children}</div>
);

export const Variants = () => (
  <Surface>
    <Button>Default</Button>
    <Button variant="secondary">Secondary</Button>
    <Button variant="outline">Outline</Button>
    <Button variant="destructive">Destructive</Button>
    <Button variant="ghost">Ghost</Button>
    <Button variant="link">Link</Button>
  </Surface>
);

export const Sizes = () => (
  <Surface>
    <Button size="sm">Small</Button>
    <Button size="default">Default</Button>
    <Button size="lg">Large</Button>
    <Button size="icon" aria-label="Search"><Search /></Button>
  </Surface>
);

export const WithIcon = () => (
  <Surface>
    <Button><TrendingUp /> Add signal</Button>
    <Button variant="outline"><Search /> Search ticker</Button>
  </Surface>
);

export const Disabled = () => (
  <Surface>
    <Button disabled>Default</Button>
    <Button variant="outline" disabled>Outline</Button>
  </Surface>
);
