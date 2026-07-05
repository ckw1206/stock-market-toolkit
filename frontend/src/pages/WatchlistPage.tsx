import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Star, TrendingUp, BarChart3, Loader2, X, ArrowUpDown } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { useWatchlist } from "../hooks/useWatchlist";
import WatchlistButton from "../components/common/WatchlistButton";
import type { WatchlistItem } from "../api/watchlistApi";

const ALL_TAGS = "__all__";
type SortKey = "added" | "symbol";

function NoteField({ item, onSave }: { item: WatchlistItem; onSave: (note: string) => void }) {
  const [value, setValue] = useState(item.note ?? "");
  return (
    <textarea
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={() => {
        if (value !== (item.note ?? "")) onSave(value);
      }}
      placeholder="Add a note (e.g. why you're watching this, entry plan)…"
      rows={1}
      className="w-full resize-none rounded-md border border-transparent bg-transparent px-1 py-0.5 text-sm text-muted-foreground placeholder:text-muted-foreground/60 hover:border-input focus:border-input focus:outline-none"
    />
  );
}

function TagEditor({ item, onSave }: { item: WatchlistItem; onSave: (tags: string[]) => void }) {
  const [input, setInput] = useState("");

  const addTag = () => {
    const next = input
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);
    if (next.length === 0) return;
    const merged = Array.from(new Set([...item.tags, ...next]));
    onSave(merged);
    setInput("");
  };

  const removeTag = (tag: string) => {
    onSave(item.tags.filter((t) => t !== tag));
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {item.tags.map((tag) => (
        <Badge key={tag} variant="secondary" className="gap-1 text-xs">
          {tag}
          <button
            type="button"
            onClick={() => removeTag(tag)}
            className="cursor-pointer text-muted-foreground hover:text-destructive"
            aria-label={`Remove tag ${tag}`}
          >
            <X className="size-3" />
          </button>
        </Badge>
      ))}
      <Input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            addTag();
          }
        }}
        onBlur={addTag}
        placeholder="+ tag"
        className="h-6 w-20 border-none bg-transparent px-1 text-xs shadow-none focus-visible:ring-1"
      />
    </div>
  );
}

export default function WatchlistPage() {
  const navigate = useNavigate();
  const { items, loading, error, refresh, update } = useWatchlist();
  const [activeTag, setActiveTag] = useState(ALL_TAGS);
  const [sortKey, setSortKey] = useState<SortKey>("added");

  const allTags = useMemo(() => {
    const s = new Set<string>();
    items.forEach((i) => i.tags.forEach((t) => s.add(t)));
    return Array.from(s).sort();
  }, [items]);

  const visibleItems = useMemo(() => {
    const filtered =
      activeTag === ALL_TAGS ? items : items.filter((i) => i.tags.includes(activeTag));
    const sorted = [...filtered];
    if (sortKey === "symbol") {
      sorted.sort((a, b) => a.symbol.localeCompare(b.symbol));
    } else {
      sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }
    return sorted;
  }, [items, activeTag, sortKey]);

  const handleSaveNote = async (symbol: string, note: string) => {
    try {
      await update(symbol, { note });
    } catch {
      /* ignore */
    }
  };

  const handleSaveTags = async (symbol: string, tags: string[]) => {
    try {
      await update(symbol, { tags });
    } catch {
      /* ignore */
    }
  };

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
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSortKey((k) => (k === "added" ? "symbol" : "added"))}
          >
            <ArrowUpDown className="mr-1 size-3.5" />
            {sortKey === "added" ? "Recently added" : "Symbol A-Z"}
          </Button>
          <Button variant="outline" onClick={refresh} disabled={loading}>
            {loading ? <Loader2 className="mr-1 size-4 animate-spin" /> : null}
            Refresh
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive mb-4">{error}</p>}

      {items.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <Star className="size-8 text-muted-foreground" />
            <p className="text-muted-foreground">Your watchlist is empty</p>
            <p className="text-xs text-muted-foreground">
              Star tickers from the Dashboard or Compare page to add them here
            </p>
            <Button onClick={() => navigate("/")}>Browse stocks</Button>
          </CardContent>
        </Card>
      ) : (
        <>
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

          <div className="flex flex-col gap-3">
            {visibleItems.map((item) => (
              <Card key={item.id}>
                <CardContent className="flex flex-col gap-2 py-4">
                  <div className="flex items-center gap-4">
                    <WatchlistButton symbol={item.symbol} className="!text-yellow-500" />
                    <span
                      className="flex-1 font-bold text-base cursor-pointer hover:underline"
                      onClick={() => navigate(`/?symbol=${item.symbol}`)}
                    >
                      {item.symbol}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Added {new Date(item.created_at).toLocaleDateString()}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/?symbol=${item.symbol}`)}
                    >
                      <TrendingUp />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/compare?symbols=${item.symbol}`)}
                    >
                      <BarChart3 />
                    </Button>
                  </div>
                  <NoteField item={item} onSave={(note) => handleSaveNote(item.symbol, note)} />
                  <TagEditor item={item} onSave={(tags) => handleSaveTags(item.symbol, tags)} />
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
