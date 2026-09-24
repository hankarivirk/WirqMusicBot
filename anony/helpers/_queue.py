from typing import Dict, List, Optional, Any

class QueueManager:
    def __init__(self):
        self._queues: Dict[int, List[Dict[str, Any]]] = {}

    def get_queue(self, chat_id: int) -> List[Dict[str, Any]]:
        return self._queues.setdefault(chat_id, [])

    def add_to_queue(self, chat_id: int, track: Dict[str, Any]) -> int:
        q = self.get_queue(chat_id)
        q.append(track)
        return len(q)

    def add_front(self, chat_id: int, track: Dict[str, Any]):
        q = self.get_queue(chat_id)
        q.insert(0, track)

    def pop_queue(self, chat_id: int) -> Optional[Dict[str, Any]]:
        q = self.get_queue(chat_id)
        return q.pop(0) if q else None

    def clear_queue(self, chat_id: int):
        self.get_queue(chat_id).clear()

Queues = QueueManager()
