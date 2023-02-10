
# Music player object to track playback queue and channel message
# In the future this can handle stored playlists and tracks

# One Player per voice channel
#   Multiple message windows for each text channel using
#   Each message window has same content

import asyncio, traceback
from enum import Enum

from .download import Downloader
from .events import Events

# States of the Player
class PlayerState(Enum):
    STOPPED = 0     # nothing
    PLAYING = 1     # playing
    PAUSED = 2      # paused
    WAITING = 3     # track that should be playing still downloading


# Track name and downloaded flag
Track = list[str, bool]

class Player:
    """Holds audio playback info"""

    def __init__(self, text_channel_id: int, msg_id: int, open_cb=None, screen_cb=None, close_cb=None) -> None:
        self.queue: list[Track] = []
        self.current: Track = None

        # Message ids for each text channel
        self.msg_ids = {}
        if msg_id is not None:
            self.msg_ids[text_channel_id] = msg_id
        self.focus_msg = msg_id

        # Window update events
        self.player_events = Events()
        self.player_events.on('open', open_cb)
        self.player_events.on('status', screen_cb)
        self.player_events.on('close', close_cb)

        # State stuff
        self.state: PlayerState = PlayerState.WAITING
        self.connected = False
        self.loaded_track = None
        self.loaded_track_downloaded = False
        self.exist = True
        self.in_playback = False
        
        self.loop = asyncio.get_event_loop()


    # Set the message ID for a text channel
    def set_text_channel_msg(self, channel_id: int, msg_id: int) -> None:
        self.msg_ids[channel_id] = msg_id
        self.focus_msg = msg_id
    
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

    async def queue(self, track):
        pass
        

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