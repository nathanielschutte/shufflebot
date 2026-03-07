import os
import asyncio
import random
import spotipy  # type: ignore
from spotipy.oauth2 import SpotifyOAuth  # type: ignore
from typing import Optional, List, Tuple

from shuffle.player.stream import Stream
from shuffle.player.models.Track import Track
from shuffle.log import shuffle_logger

# Maximum tracks to pull from an album or playlist
COLLECTION_TRACK_LIMIT = 100


class SpotifyStream(Stream):
    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)
        self.logger = shuffle_logger('spotify')

        self.pipe_path = '/tmp/spotify_pipe'
        self.device_name = "ShuffleBot"
        self.device_id = None

        # User Auth is REQUIRED to control playback.
        # Must set SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI in .env
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

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _setup(self) -> None:
        """Find the librespot device in Spotify's device list."""
        try:
            if self.sp is None:
                self.logger.error("Spotify client not initialized")
                return

            self.device_id = None
            self.ready = False

            devices = self.sp.devices()
            for d in devices.get('devices', []):
                if d['name'] == self.device_name:
                    self.device_id = d['id']
                    self.logger.info(f"Found Librespot device: {self.device_name} ({self.device_id})")
                    self.ready = True
                    break

            if not self.device_id:
                self.logger.warning(
                    f"Could not find device '{self.device_name}'. Make sure librespot is running."
                )
        except Exception as e:
            self.logger.error(f"Spotify Setup Error: {e}")

    def _make_track(self, track_info: dict) -> Optional[Track]:
        """
        Convert a Spotify track dict (from any endpoint) into a Track object.
        Returns None if the track info is incomplete or unplayable.
        """
        if not track_info:
            return None

        # Tracks inside album/playlist responses may be nested under a 'track' key
        if 'track' in track_info and isinstance(track_info['track'], dict):
            track_info = track_info['track']

        # Skip local files — they have no Spotify URI and can't be played via librespot
        if track_info.get('is_local', False):
            self.logger.debug(f"Skipping local file: {track_info.get('name', 'unknown')}")
            return None

        uri = track_info.get('uri')
        track_id = track_info.get('id')
        if not uri or not track_id:
            return None

        artists = track_info.get('artists', [])
        artist_name = artists[0]['name'] if artists else 'Unknown Artist'
        title = f"{track_info.get('name', 'Unknown')} - {artist_name}"
        web_url = track_info.get('external_urls', {}).get('spotify', '')
        duration = track_info.get('duration_ms', 0) // 1000

        # Capture uri/device_id in closure so the lambda is self-contained
        captured_uri = uri
        captured_title = title

        def start_playback() -> None:
            self.logger.info(f"Triggering playback for '{captured_title}' on {self.device_name}")
            try:
                self.sp.start_playback(device_id=self.device_id, uris=[captured_uri])
            except Exception as exc:
                self.logger.error(f"Error triggering playback: {exc}")

        return Track(
            id=track_id,
            title=title,
            query=web_url or uri,
            web_url=web_url,
            audio_url=self.pipe_path,
            duration=duration,
            source='spotify_spoof',
            on_start=start_playback,
        )

    # -------------------------------------------------------------------------
    # Public: type detection
    # -------------------------------------------------------------------------

    def detect_spotify_type(self, query: str) -> str:
        """
        Inspect a query string and return one of:
          'album', 'playlist', 'track', 'search'

        Only URL-based detection is used — no network calls made here.
        """
        q = query.strip()
        if 'spotify.com/album' in q or q.startswith('spotify:album:'):
            return 'album'
        if 'spotify.com/playlist' in q or q.startswith('spotify:playlist:'):
            return 'playlist'
        if 'spotify.com/track' in q or q.startswith('spotify:track:'):
            return 'track'
        return 'search'

    # -------------------------------------------------------------------------
    # Public: single track
    # -------------------------------------------------------------------------

    def get_track(self, query: str) -> Optional[Track]:
        """Get a single track from Spotify for playback via the librespot pipe."""
        if self.sp is None:
            self.logger.error("Spotify client not initialized")
            return None

        if not self.ready:
            self._setup()
            if not self.ready:
                return None

        try:
            spotify_type = self.detect_spotify_type(query)

            if spotify_type == 'track':
                track_info = self.sp.track(query)
            else:
                # Treat as a search query
                results = self.sp.search(q=query, limit=1, type='track')
                if not results or not results['tracks']['items']:
                    return None
                track_info = results['tracks']['items'][0]

            return self._make_track(track_info)

        except Exception as e:
            self.logger.error(f"Error getting track: {e}")
            return None

    # -------------------------------------------------------------------------
    # Public: collections (albums & playlists)
    # -------------------------------------------------------------------------

    def get_collection_tracks(self, query: str) -> Tuple[Optional[List[Track]], str]:
        """
        Fetch up to COLLECTION_TRACK_LIMIT tracks from a Spotify album or playlist.

        Returns a tuple of (tracks, collection_name).
        tracks is None on error, or an empty list if nothing playable was found.

        Safety notes:
          - Uses the standard Spotify Web API (metadata only) via spotipy.
          - No audio requests are made here; audio is triggered one at a time by the player.
          - A single paginated fetch per collection — normal API usage, no rate-limit risk.
        """
        if self.sp is None:
            self.logger.error("Spotify client not initialized")
            return None, ''

        if not self.ready:
            self._setup()
            if not self.ready:
                return None, ''

        spotify_type = self.detect_spotify_type(query)

        try:
            if spotify_type == 'album':
                return self._fetch_album_tracks(query)
            elif spotify_type == 'playlist':
                return self._fetch_playlist_tracks(query)
            else:
                self.logger.error(f"get_collection_tracks called with non-collection query: {query}")
                return None, ''
        except Exception as e:
            self.logger.error(f"Error fetching collection '{query}': {e}")
            return None, ''

    def _fetch_album_tracks(self, query: str) -> Tuple[Optional[List[Track]], str]:
        """Fetch tracks from a Spotify album URL/URI."""
        try:
            # Get album metadata for the name
            album_info = self.sp.album(query)
            album_name = album_info.get('name', 'Unknown Album')
            artist_name = ''
            artists = album_info.get('artists', [])
            if artists:
                artist_name = artists[0].get('name', '')
            collection_name = f"{album_name} — {artist_name}" if artist_name else album_name

            self.logger.info(f"Fetching album tracks for: {collection_name}")

            # album_tracks returns a paged object; we only need the first page (max 50)
            # For albums with >50 tracks (rare) we make a second call to stay under the cap.
            raw_items: List[dict] = []
            page = self.sp.album_tracks(query, limit=50)

            while page and len(raw_items) < COLLECTION_TRACK_LIMIT:
                raw_items.extend(page.get('items', []))
                if page.get('next') and len(raw_items) < COLLECTION_TRACK_LIMIT:
                    page = self.sp.next(page)
                else:
                    break

            raw_items = raw_items[:COLLECTION_TRACK_LIMIT]

            # album_tracks items are already track objects (no extra nesting)
            tracks = [t for t in (self._make_track(item) for item in raw_items) if t is not None]
            self.logger.info(f"Album '{collection_name}': {len(tracks)} playable tracks queued")
            return tracks, collection_name

        except Exception as e:
            self.logger.error(f"Error fetching album: {e}")
            return None, ''

    def _fetch_playlist_tracks(self, query: str) -> Tuple[Optional[List[Track]], str]:
        """Fetch tracks from a Spotify playlist URL/URI."""
        try:
            # Get playlist metadata for the name
            # Use fields param to minimise payload — we only want name + tracks
            playlist_info = self.sp.playlist(query, fields='name,tracks')
            collection_name = playlist_info.get('name', 'Unknown Playlist')

            self.logger.info(f"Fetching playlist tracks for: {collection_name}")

            raw_items: List[dict] = []
            # playlist() already includes the first page of tracks
            page = playlist_info.get('tracks')

            while page and len(raw_items) < COLLECTION_TRACK_LIMIT:
                for item in page.get('items', []):
                    if item and item.get('track'):
                        raw_items.append(item)
                    if len(raw_items) >= COLLECTION_TRACK_LIMIT:
                        break

                if page.get('next') and len(raw_items) < COLLECTION_TRACK_LIMIT:
                    page = self.sp.next(page)
                else:
                    break

            raw_items = raw_items[:COLLECTION_TRACK_LIMIT]

            # playlist items have {'track': {...}} structure; _make_track handles the unwrapping
            tracks = [t for t in (self._make_track(item) for item in raw_items) if t is not None]
            self.logger.info(f"Playlist '{collection_name}': {len(tracks)} playable tracks queued")
            return tracks, collection_name

        except Exception as e:
            self.logger.error(f"Error fetching playlist: {e}")
            return None, ''

    # -------------------------------------------------------------------------
    # Public: autoplay recommendation
    # -------------------------------------------------------------------------

    def get_recommendation(self, seed_track_id: str) -> Optional[Track]:
        """
        Get a recommended track based on a seed track ID via Spotify's recommendations API.
        This is bot-side autoplay — NOT librespot's built-in autoplay (which causes skip loops).
        """
        if self.sp is None or not self.ready:
            self.logger.error("Spotify not ready for recommendations")
            return None

        try:
            self.logger.debug(f"Fetching recommendation for seed track: {seed_track_id}")

            results = self.sp.recommendations(seed_tracks=[seed_track_id], limit=5)

            if not results or not results.get('tracks'):
                self.logger.warning("No recommendations returned")
                return None

            rec = random.choice(results['tracks'])
            return self._make_track(rec)

        except Exception as e:
            self.logger.error(f"Error getting recommendation: {e}")
            return None

    # -------------------------------------------------------------------------
    # Public: service management
    # -------------------------------------------------------------------------

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

    def is_ready(self) -> bool:
        return self.ready
