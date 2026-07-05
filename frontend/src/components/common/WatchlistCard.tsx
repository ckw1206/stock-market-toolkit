import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, BarChart3 } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Input } from "../ui/input";
import { useWatchlist } from "../../hooks/useWatchlist";
import WatchlistButton from "./WatchlistButton";

interface WatchlistCardProps {
  item: {
    id: number;
    symbol: string;
    note: string | null;
    tags: string[];
    created_at: string;
  };
}

function NoteEditor({ item, onSave }: { item: WatchlistCardProps["item"]; onSave: (note: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(item.note ?? "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const startEdit = () => {
    setValue(item.note ?? "");
    setEditing(true);
  };

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.selectionStart = textareaRef.current.value.length;
    }
  }, [editing]);

  const commit = () => {
    const trimmed = value.trim();
    const current = item.note ?? "";
    if (trimmed !== current) {
      onSave(trimmed === "" ? "" : trimmed);
    }
    setEditing(false);
  };

  const cancel = () => {
    setValue(item.note ?? "");
    setEditing(false);
  };

  if (editing) {
    return (
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.preventDefault();
            cancel();
          }
        }}
        rows={2}
        className="w-full resize-none rounded-md border border-input bg-background px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        placeholder="Add a note…"
      />
    );
  }

  return (
    <p
      onClick={startEdit}
      className="cursor-text text-sm text-muted-foreground hover:text-foreground min-h-[1.5rem]"
      title="Click to edit note"
    >
      {item.note || (
        <span className="text-muted-foreground/50 italic">Click to add note…</span>
      )}
    </p>
  );
}

function TagChips({ item, onSave }: { item: WatchlistCardProps["item"]; onSave: (tags: string[]) => void }) {
  const [showInput, setShowInput] = useState(false);
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (showInput && inputRef.current) inputRef.current.focus();
  }, [showInput]);

  const addTag = () => {
    const next = input
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter((t) => t.length > 0 && !item.tags.includes(t));
    if (next.length === 0) {
      setInput("");
      setShowInput(false);
      return;
    }
    onSave([...item.tags, ...next]);
    setInput("");
    setShowInput(false);
  };

  const removeTag = (tag: string) => {
    onSave(item.tags.filter((t) => t !== tag));
  };

  return (
    <div
      className="flex flex-wrap items-center gap-1.5"
      onMouseLeave={() => {
        if (input.trim() === "") setShowInput(false);
      }}
    >
      {item.tags.map((tag) => (
        <Badge key={tag} variant="secondary" className="gap-1 text-xs">
          {tag}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              removeTag(tag);
            }}
            className="cursor-pointer text-muted-foreground hover:text-destructive"
            aria-label={`Remove tag ${tag}`}
          >
            ×
          </button>
        </Badge>
      ))}

      {showInput ? (
        <Input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            } else if (e.key === "Escape") {
              setInput("");
              setShowInput(false);
            }
          }}
          onBlur={addTag}
          placeholder="tag, tag2…"
          className="h-6 w-24 border-none bg-transparent px-1 text-xs shadow-none focus-visible:ring-1"
        />
      ) : (
        <button
          type="button"
          onClick={() => setShowInput(true)}
          className="flex h-6 items-center rounded-md border border-dashed border-muted-foreground/40 px-2 text-xs text-muted-foreground hover:border-muted-foreground/70 hover:text-muted-foreground"
        >
          + tag
        </button>
      )}
    </div>
  );
}

export default function WatchlistCard({ item }: WatchlistCardProps) {
  const navigate = useNavigate();
  const { update } = useWatchlist();

  const handleSaveNote = async (note: string) => {
    try {
      await update(item.symbol, { note: note === "" ? "" : note });
    } catch {
      /* silent — card stays editable */
    }
  };

  const handleSaveTags = async (tags: string[]) => {
    try {
      await update(item.symbol, { tags });
    } catch {
      /* silent */
    }
  };

  return (
    <Card>
      <CardContent className="flex flex-col gap-2.5 py-4">
        {/* Top row: star, symbol, date, nav buttons */}
        <div className="flex items-center gap-3">
          <WatchlistButton symbol={item.symbol} className="!text-yellow-500 shrink-0" />
          <span
            className="flex-1 cursor-pointer font-bold text-base hover:underline"
            onClick={() => navigate(`/?symbol=${item.symbol}`)}
          >
            {item.symbol}
          </span>
          <span className="text-xs text-muted-foreground shrink-0">
            {new Date(item.created_at).toLocaleDateString()}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0"
            onClick={() => navigate(`/?symbol=${item.symbol}`)}
            aria-label="View chart"
          >
            <TrendingUp className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0"
            onClick={() => navigate(`/compare?symbols=${item.symbol}`)}
            aria-label="Compare"
          >
            <BarChart3 className="size-4" />
          </Button>
        </div>

        {/* Tag chips row */}
        <TagChips item={item} onSave={handleSaveTags} />

        {/* Note row */}
        <NoteEditor item={item} onSave={handleSaveNote} />
      </CardContent>
    </Card>
  );
}