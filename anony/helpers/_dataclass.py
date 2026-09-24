from dataclasses import dataclass
from typing import Optional

@dataclass
class TrackInfo:
    title: str
    link: str
    duration: str
    stream_url: str
    id: Optional[str] = None
    thumb: Optional[str] = None
    requester: Optional[str] = None
