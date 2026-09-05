# yt-search-python-legacy → Wirq Music Bot compatibility patch

Wirq Music Bot is written against `py-yt-search` (`from py_yt import Playlist,
VideosSearch`). That package wasn't usable, so this patch vendors the
`yt-search-python-legacy` fork you provided and shims it to the same API.

## What changed

- **Added `youtubesearchpython/`** at the project root — the legacy fork,
  copied as-is (its only dependency is `httpx`).
- **Added `py_yt/`** at the project root — a small compatibility package.
  It re-exports `youtubesearchpython.future`'s async classes (`Playlist`,
  `VideosSearch`, etc.) under the `py_yt` name Wirq Music Bot already imports,
  so `anony/core/youtube.py` and `anony/plugins/iquery.py` needed **no
  changes**.
- **`VideosSearch` wrapper**: Wirq Music Bot calls `VideosSearch(query,
  limit=1, with_live=False)`. The legacy fork uses `is_live` instead of
  `with_live`, and only supports "videos only" or "livestreams only" (no
  mixed mode). The shim accepts `with_live` for compatibility and maps it
  onto the fork's default "videos only" search — which is exactly what
  Wirq Music Bot's only real call site (`with_live=False`) wants. `Playlist`
  needed no wrapper; `Playlist.get(url)` already returns a `dict` with a
  `videos` key, matching what `anony/core/youtube.py` expects.
- **`requirements.txt` / `pyproject.toml`**: removed `py-yt-search`,
  added `httpx>=0.28.1,<1.0` (the vendored library's one dependency).

## Verified

- Both `py_yt` import sites (`anony/core/youtube.py`,
  `anony/plugins/iquery.py`) resolve correctly against the vendored code,
  including the `with_live` kwarg mismatch above.
- Result dict schema (`id`, `title`, `duration`, `thumbnails`, `channel`,
  `viewCount`, `link`) matches field-for-field what `anony/core/youtube.py`
  reads.
- Not verified: actual live YouTube requests — this sandbox has no network
  access, so only imports/signatures/schema were checked, not a real
  search/playlist round-trip. Run a live search once deployed to confirm.

## uv.lock

`uv.lock` still references `py-yt-search`. Regenerate it with `uv lock`
after pulling this patch (or just use `pip install -r requirements.txt`,
which is already correct).

## Autoplay

Wirq Music Bot has **no autoplay feature** — there's no "autoplay",
"related", or queue-refill-on-empty logic anywhere in `anony/plugins/` or
`anony/core/`. It only plays what's explicitly queued. Your JattX bot (per
earlier work) already has autoplay with queue refill, so that logic isn't
present here and would need to be ported over separately if you want it
in Wirq Music Bot.

---

## New features added on top of the compatibility patch

### 1. Autoplay ("up next", not "similar")
- `/autoplay on` / `/autoplay off` (also toggleable from `/settings`).
- When the queue empties and autoplay is on, `anony/core/calls.py` calls
  the new `yt.related(video_id, exclude)` (`anony/core/youtube.py`),
  which uses YouTube's own **watch-next** data — the same feed that
  powers the real "Up next" panel — via the vendored library's
  `Recommendations.get()`. This is not a generic "similar songs" search;
  it's the actual next-up queue YouTube itself would suggest.
- **No repeats**: every autoplay pick is checked against
  `queue.excluded_ids(chat_id)` (`anony/helpers/_queue.py`), which is the
  union of recently-played track IDs *and* whatever's still sitting in
  the queue — so autoplay can't suggest a song that already played in
  this session or one that's already queued up. History is per-chat,
  capped at the last 50 plays, and clears when the stream stops.
- Live streams in the recommendations feed are skipped automatically.

### 2. Full playlist add + website view for long playlists
- `PLAYLIST_LIMIT` default raised from 20 → 200 (`config.py`, still
  overridable via env var) — `/play <playlist url>` now queues the whole
  playlist for typical sizes instead of just the first 20.
- Playlists over 20 tracks (`PLAYLIST_WEB_THRESHOLD` in
  `anony/plugins/play.py`) are no longer dumped into a truncated chat
  message. Instead, `anony/helpers/_telegraph.py` publishes the full
  tracklist (with clickable links) to a Telegra.ph page, and the chat
  gets a compact "📜 View full playlist" button linking to it — the same
  Telegraph service Wirq Music Bot already relies on for thumbnails
  (`DEFAULT_THUMB` is a `te.legra.ph` link). Shorter playlists still show
  inline, as before.

### 3. YouTube Music audio-only source, with fallback
- `yt.download()` now tries `https://music.youtube.com/watch?v=<id>`
  first when downloading audio — an audio-only source, so yt-dlp doesn't
  need to probe video formats, meaning faster extraction and a quicker
  download start. If a track isn't available on YouTube Music (e.g. it's
  not a music upload), it automatically falls back to the regular
  `youtube.com` watch page. Video downloads (`/vplay`) are unaffected —
  YouTube Music doesn't serve video, so those still go straight to
  `youtube.com`.

### Testing note
This sandbox has no network access, so none of the above could be
exercised against real YouTube/Telegraph traffic. What *was* verified
offline:
- All edited/added files byte-compile cleanly.
- `related()`, `playlist()`, and the `music.youtube.com → youtube.com`
  download fallback were tested against mocked dependencies and behave
  exactly as designed (correct skipping of excluded/live entries, correct
  fallback order, no crashes on API errors).
- The queue history/exclusion logic (`excluded_ids`) was tested directly
  and correctly unions history + current queue, and clears on stop.

Please do a live smoke test once deployed (`/play <playlist url>`,
`/autoplay on` and let a queue run out, and a normal `/play <song>`) to
confirm real-world YouTube/YT Music/Telegraph behavior.
