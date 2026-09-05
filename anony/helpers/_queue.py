# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import asyncio
from collections import defaultdict, deque
from typing import Union

from ._dataclass import Media, Track

MediaItem = Union[Media, Track]


class Queue:
    def __init__(self):
        self.queues: dict[int, deque[MediaItem]] = defaultdict(deque)
        # Recently played track IDs per chat, used to keep autoplay from
        # repeating a song that was already played or is still queued.
        # This is an in-memory cache backed by the DB (see remember()/
        # get_history()) so history survives a restart instead of being
        # RAM-only.
        self.history: dict[int, deque[str]] = defaultdict(lambda: deque(maxlen=50))
        self._history_loaded: set[int] = set()
        # Per-chat lock so concurrent /skip, /playforce, stream-end, and
        # autoplay callbacks can't race each other on the same queue.
        self.locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def lock(self, chat_id: int) -> asyncio.Lock:
        """Return the asyncio.Lock guarding this chat's queue."""
        return self.locks[chat_id]

    def add(self, chat_id: int, item: MediaItem) -> int:
        """Add an item to the queue and return its 0-based index in the
        queue (0 means the queue was empty and this item is now the
        currently playing track)."""
        self.queues[chat_id].append(item)
        return len(self.queues[chat_id]) - 1

    def check_item(self, chat_id: int, item_id: str) -> tuple[int, MediaItem | None]:
        """Check if an item with the given ID exists in the queue."""
        pos, track = next(
            (
                (i, track)
                for i, track in enumerate(list(self.queues[chat_id]))
                if track.id == item_id
            ),
            (-1, None),
        )
        return pos, track

    def force_add(
        self, chat_id: int, item: MediaItem, remove: int | bool = False
    ) -> None:
        """Replace the currently playing item with a new one."""
        self.remove_current(chat_id)
        self.queues[chat_id].appendleft(item)
        if remove:
            self.queues[chat_id].rotate(-remove)
            self.queues[chat_id].popleft()
            self.queues[chat_id].rotate(remove)

    def get_current(self, chat_id: int) -> MediaItem | None:
        """Return the currently playing item (first in queue), if any."""
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_next(self, chat_id: int, check: bool = False) -> MediaItem | None:
        """Remove current item and return the next one, or None if empty."""
        if not self.queues[chat_id]:
            return None
        if check:
            return self.queues[chat_id][1] if len(self.queues[chat_id]) > 1 else None

        self.queues[chat_id].popleft()
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_queue(self, chat_id: int) -> list[MediaItem]:
        """Return the full queue including the currently playing item."""
        return list(self.queues[chat_id])

    def remove_current(self, chat_id: int) -> None:
        """Remove the currently playing item only (if exists)."""
        if self.queues[chat_id]:
            self.queues[chat_id].popleft()

    def clear(self, chat_id: int) -> None:
        """Clear the entire queue."""
        self.queues[chat_id].clear()

    async def remember(self, chat_id: int, item_id: str) -> None:
        """Record a track ID as played, for autoplay dedup. Persisted to
        the DB so this survives a restart."""
        from anony import db

        if item_id:
            await self._ensure_history_loaded(chat_id)
            self.history[chat_id].append(item_id)
            await db.add_autoplay_history(chat_id, item_id)

    async def _ensure_history_loaded(self, chat_id: int) -> None:
        from anony import db

        if chat_id in self._history_loaded:
            return
        self._history_loaded.add(chat_id)
        for track_id in await db.get_autoplay_history(chat_id):
            self.history[chat_id].append(track_id)

    async def get_history(self, chat_id: int) -> set[str]:
        """Return the set of recently played track IDs for a chat."""
        await self._ensure_history_loaded(chat_id)
        return set(self.history[chat_id])

    async def clear_history(self, chat_id: int) -> None:
        """Clear the recently-played history for a chat."""
        from anony import db

        self.history[chat_id].clear()
        self._history_loaded.add(chat_id)
        await db.clear_autoplay_history(chat_id)

    async def excluded_ids(self, chat_id: int) -> set[str]:
        """IDs autoplay should never re-suggest: history + whatever's still queued."""
        history = await self.get_history(chat_id)
        return history | {
            item.id for item in self.queues[chat_id] if item.id
        }
