
from abc import ABC

from shuffle.player.models.Track import Track

class Stream(ABC):
    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id

    def download(self, video_hash: str, path: str) -> None:
        ...
    
    def get_track(self, query: str) -> Track:
        ...

    def is_ready(self) -> bool:
        ...
