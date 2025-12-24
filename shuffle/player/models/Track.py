
from typing import Any, Callable, Optional

from dataclasses import dataclass

@dataclass
class Track:
    id: str
    title: str
    query: str
    web_url: str
    audio_url: str
    channel: Any = None
    duration: int = -1
    source: str = 'youtube'
    status: str = 'queued'
    downloaded: bool = False
    # Trigger function to start playback (used for Spotify Spoof)
    on_start: Optional[Callable] = None
    from_autoplay: bool = False
