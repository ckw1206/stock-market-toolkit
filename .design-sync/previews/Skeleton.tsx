import { Skeleton } from "frontend";

export const Card = () => (
  <div className="bg-background text-foreground p-6">
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-4 w-[280px]">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>
      <Skeleton className="h-24 w-full rounded-md" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
    </div>
  </div>
);

export const Lines = () => (
  <div className="bg-background text-foreground p-6 flex flex-col gap-2 w-[240px]">
    <Skeleton className="h-4 w-full" />
    <Skeleton className="h-4 w-5/6" />
    <Skeleton className="h-4 w-2/3" />
  </div>
);
