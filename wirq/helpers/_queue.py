# Wirq Music Bot - Per-Group Queue Manager (Section 2)
import random
import asyncio
from collections import defaultdict, deque
from typing import List, Optional, Union, Set
from wirq.helpers._dataclass import Track, Media

MediaItem = Union[Media, Track]

class Queue:
    def __init__(self):
        self.queues: dict[int, deque[MediaItem]] = defaultdict(deque)
        self.history: dict[int, deque[str]] = defaultdict(lambda: deque(maxlen=50))
        self._locks = defaultdict(asyncio.Lock)

    def lock(self, chat_id: int) -> asyncio.Lock:
        return self._locks[chat_id]

    def add(self, chat_id: int, item: MediaItem) -> int:
        self.queues[chat_id].append(item)
        return len(self.queues[chat_id]) - 1

    def put(self, chat_id: int, item: MediaItem) -> int:
        return self.add(chat_id, item)

    def force_play_new(self, chat_id: int, item: MediaItem):
        self.queues[chat_id].appendleft(item)

    def get_current(self, chat_id: int) -> Optional[MediaItem]:
        q = self.queues.get(chat_id)
        return q[0] if q and len(q) > 0 else None

    def get_next(self, chat_id: int, check: bool = False) -> Optional[MediaItem]:
        q = self.queues.get(chat_id)
        if not q:
            return None
        if check:
            return q[1] if len(q) > 1 else None
        return q.popleft() if q else None

    def get_queue(self, chat_id: int) -> List[MediaItem]:
        return list(self.queues.get(chat_id, []))

    def get_all(self, chat_id: int) -> List[MediaItem]:
        return self.get_queue(chat_id)

    def clear(self, chat_id: int):
        self.queues.pop(chat_id, None)

    def clear_upcoming(self, chat_id: int):
        q = self.queues.get(chat_id)
        if q:
            current = q[0]
            self.queues[chat_id] = deque([current])

    def shuffle(self, chat_id: int) -> bool:
        q = self.queues.get(chat_id)
        if not q or len(q) <= 2:
            return False
        # Preserve current playing track at index 0, shuffle the rest
        current = q.popleft()
        rest = list(q)
        random.shuffle(rest)
        self.queues[chat_id] = deque([current] + rest)
        return True

    async def clear_history(self, chat_id: int):
        self.history.pop(chat_id, None)

    async def remember(self, chat_id: int, track_id: str):
        self.history[chat_id].append(track_id)

    async def get_history(self, chat_id: int) -> Set[str]:
        return set(self.history.get(chat_id, []))

    async def excluded_ids(self, chat_id: int) -> Set[str]:
        return await self.get_history(chat_id)
