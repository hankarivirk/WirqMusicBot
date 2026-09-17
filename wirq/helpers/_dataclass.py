from dataclasses import dataclass
from typing import Optional

@dataclass
class Media:
    id: str
    duration: str = "00:00"
    duration_sec: int = 0
    file_path: Optional[str] = None
    message_id: int = 0
    title: Optional[str] = None
    url: Optional[str] = None
    time: int = 0
    user: Optional[str] = None
    video: bool = False

@dataclass
class Track:
    id: str
    channel_name: Optional[str] = None
    duration: str = "00:00"
    duration_sec: int = 0
    title: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    message_id: int = 0
    time: int = 0
    thumbnail: Optional[str] = None
    user: Optional[str] = None
    view_count: Optional[str] = None
    video: bool = False
