
from typing import List, Optional
from dataclasses import dataclass

from shuffle.player.models.Track import Track

@dataclass
class Queue:
    def __init__(self) -> None:
        self.queue: List[Track] = []
        self.current: Optional[Track] = None

    @property
    def is_empty(self) -> bool:
        return len(self.queue) == 0

    @property
    def is_playing(self) -> bool:
        if self.current is None:
            return False

        # return self.current.status == 'playing'

        return False

        # TODO: Check if the current track is playing

    @property
    def peek(self) -> Track:
        return self.queue[0]

    @property
    def length(self) -> int:
        return len(self.queue)

    def enqueue(self, track: Track) -> None:
        self.queue.append(track)

    def pop(self) -> Track:
        track = self.queue.pop(0)
        self.current = track
        return track

    def __repr__(self) -> str:
        return f'Queue[tracks={self.length}, current={self.current}]'
