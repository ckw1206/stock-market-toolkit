import { CacheBadge } from "frontend";

// Timestamps are computed relative to render time so each state resolves to
// its live label (fresh / expiring soon / expired).
const inMinutes = (m: number) => new Date(Date.now() + m * 60_000).toISOString();

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6 flex flex-wrap items-center gap-3">{children}</div>
);

export const States = () => (
  <Surface>
    <CacheBadge expiresAt={inMinutes(9)} />
    <CacheBadge expiresAt={inMinutes(0.5)} />
    <CacheBadge expiresAt={inMinutes(-5)} />
  </Surface>
);
