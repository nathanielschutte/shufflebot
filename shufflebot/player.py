
# Music player object to track playback queue and channel message
# In the future this can handle stored playlists and tracks

# One Player per voice channel
#   Multiple message windows for each text channel using
#   Each message window has same content

from enum import Enum

from .download import Downloader

# States of the Player
class PlayerState(Enum):
    STOPPED = 0     # nothing
    PLAYING = 1     # playing
    PAUSED = 2      # paused
    WAITING = 3     # track that should be playing still downloading


# Track name and downloaded flag
Track = tuple[str, bool]

class Player:
    """Holds audio playback info"""

    def __init__(self, msg_id: int, text_channel_id: int, audiodir: str, voice_channel: str) -> None:
        self.queue = []
        self.current = None

        # message ids for each text channel
        self.msg_ids = {}
        self.msg_ids[text_channel_id] = msg_id

        # audio cache dir
        self.audiodir = audiodir

        # window content
        self.title = 'ShuffleBot'
        self.voice_channel = voice_channel
        self.state: PlayerState = PlayerState.WAITING
    
    # Queue a song
    def push(self, track) -> None:
        if self.current is None:
            self.current = track
            return True
        else:
            # NO QUEUE BOT
            return False

            self.queue.append(track)
        # print(f'player: {self}')

    # Get next track title
    def pop(self) -> str:
        if len(self.queue) > 0:
            track = self.queue[0]
            del self.queue[0]

            self.current = track

            return track
        else:
            self.current = None
            return None

    # Queue length
    def get_len(self) -> int:
        return len(self.queue)

    # Get copy of queue
    def get_queue(self) -> list:
        return self.queue.copy()

    def state_string(self):
        str = ''
        if self.state == PlayerState.PLAYING:
            str = 'playing'
        elif self.state == PlayerState.PAUSED:
            str = 'paused'
        elif self.state == PlayerState.STOPPED:
            str = 'stopped'
        elif self.state == PlayerState.WAITING:
            str = 'downloading...'
        return str

    def __str__(self) -> str:
        return f'current: {self.current} queue: {self.queue}'