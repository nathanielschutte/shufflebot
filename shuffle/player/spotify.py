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
        # must set SPOTIPY_REDIRECT_URI in .env
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            scope="user-modify-playback-state user-read-playback-state",
            open_browser=False
        ))
        
        self.ready = False
        self._setup()

    def _setup(self) -> None:
        try:
            # Reset state
            self.device_id = None
            self.ready = False
            
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

    async def restart_service(self) -> bool:
        """Restart the librespot systemd service and re-setup the stream."""
        self.logger.info("Restarting librespot service...")
        try:
            proc = await asyncio.create_subprocess_exec(
                'sudo', 'systemctl', 'restart', 'librespot',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            except asyncio.TimeoutError:
                proc.kill()
                self.logger.error("Timeout waiting for librespot restart")
                return False
            
            if proc.returncode != 0:
                self.logger.error(f"Failed to restart librespot: {stderr.decode()}")
                return False
            
            self.logger.info("Librespot service restarted, waiting for it to initialize...")
            await asyncio.sleep(5)
            
            # Re-run setup to get new device ID (this is quick, blocking is fine)
            self._setup()
            
            if self.ready:
                self.logger.info("Librespot successfully restarted and ready")
                return True
            else:
                self.logger.error("Librespot restarted but device not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Error restarting librespot: {e}")
            return False
    
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