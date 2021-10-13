
# Music player object to track playback queue and channel message
# In the future this can handle stored playlists and tracks

from .download import Downloader

class Player:
    """Holds audio playback info"""

    def __init__(self, msg, dir) -> None:
        self.queue = []
        self.msg_id = msg
        self.dir = dir
    
    # Queue a song
    def push(self, track) -> None:
        self.queue.append(track)

    # Get next track title
    def pop(self) -> str:
        if len(self.queue) > 0:
            track = self.queue[0]
            del self.queue[0]
            return track

    # Queue length
    def get_len(self) -> int:
        return len(self.queue)

    # Get copy of queue
    def get_queue(self) -> list:
        return self.queue.copy()