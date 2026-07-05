import { useMemo, useState } from "react";
import { Star, Loader2, ArrowUp, ArrowDown } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { Badge } from "../components/ui/badge";
import { useWatchlist } from "../hooks/useWatchlist";
import WatchlistCard from "../components/common/WatchlistCard";

const ALL_TAGS = "__all__";

type SortCol = "symbol" | "price" | "change" | "signal";
type SortDir = "asc" | "desc";

interface SortState {
  col: SortCol;
  dir: SortDir;
}

function SortHeader({
  col,
  sort,
  onSort,
  children,
}: {
  col: SortCol;
  sort: SortState;
  onSort: (col: SortCol) => void;
  children: React.ReactNode;
}) {
  const active = sort.col === col;
  return (
    <button
      type="button"
      onClick={() => onSort(col)}
      className={`flex items-center gap-1 text-xs font-medium uppercase tracking-wide transition-colors ${
        active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
      }`}
      aria-label={`Sort by ${col}`}
    >
      {children}
      {active && (
        sort.dir === "asc" ? (
          <ArrowUp className="size-3" />
        ) : (
          <ArrowDown className="size-3" />
        )
      )}
    </button>
  );
}

export default function WatchlistPage() {
  const { items, loading, error, refresh } = useWatchlist();
  const [activeTag, setActiveTag] = useState(ALL_TAGS);
  const [sort, setSort] = useState<SortState>({ col: "symbol", dir: "asc" });

  const allTags = useMemo(() => {
    const s = new Set<string>();
    items.forEach((i) => i.tags.forEach((t) => s.add(t)));
    return Array.from(s).sort();
  }, [items]);

  const handleSort = (col: SortCol) => {
    setSort((prev) =>
      prev.col === col
        ? { col, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { col, dir: "asc" }
    );
  };

  const visibleItems = useMemo(() => {
    const filtered =
      activeTag === ALL_TAGS
        ? items
        : items.filter((i) => i.tags.includes(activeTag));

    const sorted = [...filtered];
    sorted.sort((a, b) => {
      if (sort.col === "symbol") {
        return sort.dir === "asc"
          ? a.symbol.localeCompare(b.symbol)
          : b.symbol.localeCompare(a.symbol);
      }
      // price / change / signal — not on WatchlistItem, push all to bottom
      return a.symbol.localeCompare(b.symbol);
    });
    return sorted;
  }, [items, activeTag, sort]);

  if (loading) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        <Skeleton className="h-9 w-48" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Watchlist</h1>
        <Button variant="outline" onClick={refresh} disabled={loading}>
          {loading ? <Loader2 className="mr-1 size-4 animate-spin" /> : null}
          Refresh
        </Button>
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {items.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <Star className="size-8 text-muted-foreground" />
            <p className="text-muted-foreground">Your watchlist is empty</p>
            <p className="text-xs text-muted-foreground">
              Star tickers from the Dashboard or Compare page to add them here
            </p>
            <Button onClick={() => (window.location.href = "/")}>Browse stocks</Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Tag filter bar */}
          {allTags.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-1.5">
              <Badge
                variant={activeTag === ALL_TAGS ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => setActiveTag(ALL_TAGS)}
              >
                All
              </Badge>
              {allTags.map((tag) => (
                <Badge
                  key={tag}
                  variant={activeTag === tag ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => setActiveTag(tag)}
                >
                  {tag}
                </Badge>
              ))}
            </div>
          )}

          {/* Column headers */}
          <div className="mb-2 flex items-center gap-4 px-4">
            <div className="w-8 shrink-0" /> {/* star spacer */}
            <SortHeader col="symbol" sort={sort} onSort={handleSort}>
              Symbol
            </SortHeader>
            <div className="flex-1" /> {/* spacer for tag+note area */}
            <SortHeader col="price" sort={sort} onSort={handleSort}>
              Price
            </SortHeader>
            <SortHeader col="change" sort={sort} onSort={handleSort}>
              Change %
            </SortHeader>
            <SortHeader col="signal" sort={sort} onSort={handleSort}>
              Signal
            </SortHeader>
            <div className="w-20 shrink-0" /> {/* nav buttons spacer */}
          </div>

          {/* Card list */}
          <div className="flex flex-col gap-3">
            {visibleItems.map((item) => (
              <WatchlistCard
                key={item.id}
                item={item}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}