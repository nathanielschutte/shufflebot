import os
import time
import asyncio
import spotipy # type: ignore
from spotipy.oauth2 import SpotifyOAuth # type: ignore
from typing import Optional

from shuffle.player.stream import Stream
from shuffle.player.models.Track import Track
from shuffle.log import shuffle_logger

class SpotifyStream(Stream):
    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)
        self.logger = shuffle_logger('spotify')
        
        self.pipe_path = '/tmp/spotify_pipe'
        self.device_name = "ShuffleBot"
        self.device_id = None

        # User Auth is REQUIRED to control playback
        # You must set SPOTIPY_REDIRECT_URI in your .env (e.g., http://localhost:8888/callback)
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            scope="user-modify-playback-state user-read-playback-state",
            open_browser=False
        ))
        
        self.ready = False
        self._setup()

    def _setup(self) -> None:
        try:
            # Refresh devices
            devices = self.sp.devices()
            for d in devices['devices']:
                if d['name'] == self.device_name:
                    self.device_id = d['id']
                    self.logger.info(f"Found Librespot device: {self.device_name} ({self.device_id})")
                    self.ready = True
                    break
            
            if not self.device_id:
                self.logger.warning(f"Could not find device '{self.device_name}'. Make sure librespot is running.")
        except Exception as e:
            self.logger.error(f"Spotify Setup Error: {e}")

    def get_track(self, query: str) -> Optional[Track]:
        if not self.ready:
            self._setup()
            if not self.ready:
                return None

        try:
            # 1. Search/Resolve Track
            track_info = None
            if 'spotify.com' in query:
                track_info = self.sp.track(query)
            else:
                results = self.sp.search(q=query, limit=1, type='track')
                if results['tracks']['items']:
                    track_info = results['tracks']['items'][0]

            if not track_info:
                return None

            uri = track_info['uri']
            title = f"{track_info['name']} - {track_info['artists'][0]['name']}"
            
            # 2. Define the "Trigger" function
            # This function will be called by player.py RIGHT before playing audio
            def start_playback():
                self.logger.info(f"Triggering playback for {title} on {self.device_name}")
                self.sp.start_playback(device_id=self.device_id, uris=[uri])

            # 3. Return Track pointing to the Pipe
            return Track(
                id=track_info['id'],
                title=title,
                query=query,
                web_url=track_info['external_urls']['spotify'],
                # POINT TO THE PIPE
                audio_url=self.pipe_path, 
                duration=track_info['duration_ms'] // 1000,
                source='spotify_spoof',
                # ATTACH THE TRIGGER
                on_start=start_playback 
            )

        except Exception as e:
            self.logger.error(f"Error getting track: {e}")
            return None

    def is_ready(self) -> bool:
        return self.ready