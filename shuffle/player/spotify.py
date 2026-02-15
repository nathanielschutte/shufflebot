import os
import time
import asyncio
import random
import spotipy # type: ignore
from spotipy.oauth2 import SpotifyOAuth # type: ignore
from typing import Optional, List

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
        # must set SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI in .env
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                scope="user-modify-playback-state user-read-playback-state",
                open_browser=False
            ))
            self.ready = False
            self._setup()
        except Exception as e:
            self.logger.error(f"Spotify init error: {e}")
            self.logger.error("Check SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI in .env")
            self.sp = None
            self.ready = False

    def _setup(self) -> None:
        """Find the librespot device in Spotify's device list."""
        try:
            if self.sp is None:
                self.logger.error("Spotify client not initialized")
                return

            # Reset state
            self.device_id = None
            self.ready = False
            
            # Refresh devices
            devices = self.sp.devices()
            for d in devices.get('devices', []):
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
            
            # Wait for librespot to register with Spotify (poll for device)
            for attempt in range(6):
                await asyncio.sleep(5)
                self._setup()
                if self.ready:
                    self.logger.info(f"Librespot ready after {(attempt + 1) * 5}s")
                    return True
                self.logger.debug(f"Device not found yet, attempt {attempt + 1}/6...")
            
            self.logger.error("Librespot restarted but device not found after 30s")
            return False
                
        except Exception as e:
            self.logger.error(f"Error restarting librespot: {e}")
            return False
    
    def get_track(self, query: str) -> Optional[Track]:
        """Get a track from Spotify for playback via librespot pipe."""
        if self.sp is None:
            self.logger.error("Spotify client not initialized")
            return None

        if not self.ready:
            self._setup()
            if not self.ready:
                return None

        try:
            # 1. Search/Resolve Track
            track_info = None
            if 'spotify.com' in query or 'spotify:' in query:
                track_info = self.sp.track(query)
            else:
                results = self.sp.search(q=query, limit=1, type='track')
                if results and results['tracks']['items']:
                    track_info = results['tracks']['items'][0]

            if not track_info:
                return None

            uri = track_info['uri']
            title = f"{track_info['name']} - {track_info['artists'][0]['name']}"
            
            # 2. Define the "Trigger" function
            # This function will be called by player.py RIGHT before playing audio
            def start_playback():
                self.logger.info(f"Triggering playback for {title} on {self.device_name}")
                try:
                    self.sp.start_playback(device_id=self.device_id, uris=[uri])
                except Exception as e:
                    self.logger.error(f"Error triggering playback: {e}")

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

    def get_recommendation(self, seed_track_id: str) -> Optional[Track]:
        """
        Get a recommended track based on a seed track ID using Spotify's recommendations API.
        This is the bot-side autoplay — NOT librespot's built-in autoplay which causes skip loops.
        """
        if self.sp is None or not self.ready:
            self.logger.error("Spotify not ready for recommendations")
            return None

        try:
            self.logger.debug(f"Fetching recommendation for seed track: {seed_track_id}")
            
            results = self.sp.recommendations(
                seed_tracks=[seed_track_id],
                limit=5
            )
            
            if not results or not results.get('tracks'):
                self.logger.warning("No recommendations returned")
                return None

            # Pick a random track from the recommendations to add variety
            rec = random.choice(results['tracks'])
            
            uri = rec['uri']
            title = f"{rec['name']} - {rec['artists'][0]['name']}"
            
            self.logger.info(f"Autoplay recommendation: {title}")

            # Create the trigger function for this track
            def start_playback():
                self.logger.info(f"Triggering autoplay for {title} on {self.device_name}")
                try:
                    self.sp.start_playback(device_id=self.device_id, uris=[uri])
                except Exception as e:
                    self.logger.error(f"Error triggering autoplay: {e}")

            return Track(
                id=rec['id'],
                title=title,
                query=f"spotify:track:{rec['id']}",
                web_url=rec['external_urls']['spotify'],
                audio_url=self.pipe_path,
                duration=rec['duration_ms'] // 1000,
                source='spotify_spoof',
                on_start=start_playback
            )

        except Exception as e:
            self.logger.error(f"Error getting recommendation: {e}")
            return None

    def is_ready(self) -> bool:
        return self.ready
