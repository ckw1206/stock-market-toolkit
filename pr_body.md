## Summary

Backend implementation of ai-workflow-space/stock-market-toolkit#265 — per-symbol notes and tags for the watchlist.

### What was implemented

- **Model** (`backend/app/models/watchlist.py`): `note` (Text, nullable) and `tags` (JSON list, nullable) columns on the Watchlist model.
- **Schema** (`backend/app/schemas/watchlist.py`): `WatchlistUpdate` with `note: str | None` and `tags: list[str] | None`; `WatchlistResponse` with `note`, `tags` (list).
- **Route** (`backend/app/routes/watchlist.py`): `PATCH /api/watchlist/{symbol}` — find item by symbol (case-insensitive), update note and/or tags (tags normalized to lowercase, whitespace-stripped, deduped), 404 if not found, partial update preserved.
- **Migration** (`backend/app/alembic/versions/f4a5b6c7d8e9_add_watchlist_notes_and_tags.py`): both columns nullable.
- **Schema export** (`backend/app/schemas/__init__.py`): `WatchlistUpdate` exported.
- **Tests** (`backend/tests/test_watchlist_notes.py`): full PATCH coverage (note, tags, partial update, 404, user scoping, empty-body no-op, tag normalization/dedup, clear note with empty string) and GET list coverage.

### Acceptance criteria status

All backend criteria from the issue are satisfied by the merged PR #275 (commit 8f23c9f on main).

### Note on test environment

Test collection in this scratch environment fails due to a pre-existing missing dependency (`pandas_ta`) unrelated to this feature. The application itself is unaffected.