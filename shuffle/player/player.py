import asyncio
import os
import discord

from typing import Any, List, Optional, Tuple

from shuffle.log import shuffle_logger

from shuffle.player.youtube import YoutubeStream
from shuffle.player.spotify import SpotifyStream

from shuffle.player.models.Queue import Queue
from shuffle.player.models.Guild import Guild
from shuffle.player.models.Track import Track

# Max retries for Spotify playback failures (stale session, etc.)
SPOTIFY_MAX_RETRIES = 2


class Player:
    def __init__(self, guild_id: int, config: dict, bot: Any) -> None:
        self.guild = Guild(guild_id)
        self.queue = Queue()
        self.streams = {
            'youtube': YoutubeStream(guild_id),
            'spotify': SpotifyStream(guild_id)
        }
        self.config = config
        self.bot = bot

        self.state = 'idle'  # 'idle', 'playing', 'paused', 'stopped'

        self.client: Optional[List[Any]] = None
        # Track we were playing when paused — stored to enable resume
        self.paused_track: Optional[Track] = None

        # Bot-side autoplay: when queue is empty, fetch similar tracks via Spotify API
        self.autoplay_enabled: bool = False
        # Track the last played track's Spotify ID for recommendations
        self._last_track_id: Optional[str] = None
        self._last_track_source: Optional[str] = None

        self.log = shuffle_logger(f'player [{self.guild.id}]')
        self.log.info(f'Created player for {self.guild} with queue {self.queue}')

    # -------------------------------------------------------------------------
    # Internal playback loop
    # -------------------------------------------------------------------------

    async def _play(self, track: Track, retry_count: int = 0) -> None:
        self.log.info(f'Playing {track.title} [{track.web_url}]')

        # --- 1. Connect to Voice ---
        voice = None
        if self.client is not None:
            try:
                if self.client[0].is_connected():
                    if track.channel.id != self.client[1]:
                        await self.client[0].move_to(track.channel)
                        self.client[1] = track.channel.id
                    voice = self.client[0]
                else:
                    self.client = None
            except Exception:
                self.client = None

        if voice is None:
            if self.bot and hasattr(self.bot, 'voice_clients'):
                for vc in self.bot.voice_clients:
                    if vc.guild.id == self.guild.id:
                        voice = vc
                        self.client = [voice, track.channel.id]
                        if vc.channel.id != track.channel.id:
                            await vc.move_to(track.channel)
                        break

            if voice is None:
                try:
                    voice = await track.channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
                    self.client = [voice, track.channel.id]
                except Exception as e:
                    self.log.error(f"Connection error: {e}")
                    if not self.queue.is_empty:
                        await asyncio.sleep(1)
                        asyncio.create_task(self._play(self.queue.pop()))
                    return

        # --- 2. Create Audio Source ---
        started_playing = False
        spotify_timeout = False
        try:
            audio_source = None

            if track.source == 'spotify_spoof':
                self.log.debug("Starting Spotify Sync...")

                if track.on_start:
                    asyncio.create_task(asyncio.to_thread(track.on_start))

                try:
                    self.log.debug("Waiting for audio stream...")
                    pipe_file = await asyncio.wait_for(
                        asyncio.to_thread(open, track.audio_url, 'rb'),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    self.log.error("Spotify timed out (Librespot didn't send audio)")
                    spotify_timeout = True
                    raise Exception("Spotify Timeout")

                self.log.debug("Stream received! Piping to FFmpeg...")

                audio_source = discord.FFmpegPCMAudio(
                    pipe_file,
                    pipe=True,
                    before_options='-f s16le -ar 44100 -ac 2',
                    options='-loglevel warning'
                )
            else:
                self.log.debug("Creating YouTube Source...")
                yt_options = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                audio_source = discord.FFmpegPCMAudio(track.audio_url, **yt_options)

            def after_playing(error: Optional[Exception]) -> None:
                if error:
                    self.log.error(f'Playback error: {error}')
                else:
                    self.log.debug('Playback ended')

            voice.play(audio_source, after=after_playing)
            self.state = 'playing'
            started_playing = True
            self.log.debug("Playback started successfully")

            self._last_track_id = track.id
            self._last_track_source = track.source

        except Exception as e:
            self.log.error(f'Error creating audio source: {str(e)}')
            import traceback
            self.log.error(traceback.format_exc())

            # --- Spotify Retry Logic ---
            if spotify_timeout and track.source == 'spotify_spoof' and retry_count < SPOTIFY_MAX_RETRIES:
                self.log.info(
                    f"Attempting Spotify recovery (attempt {retry_count + 1}/{SPOTIFY_MAX_RETRIES})..."
                )
                spotify_stream = self.streams.get('spotify')
                if spotify_stream and await spotify_stream.restart_service():
                    self.log.info("Librespot restarted, re-fetching track...")
                    new_track = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: spotify_stream.get_track(track.query)
                    )
                    if new_track:
                        new_track.channel = track.channel
                        self.log.info("Retrying playback with fresh track...")
                        await self._play(new_track, retry_count + 1)
                        return
                    else:
                        self.log.error("Failed to re-fetch track after restart")
                else:
                    self.log.error("Failed to restart librespot service")

        # --- 3. Queue Handling ---
        if not started_playing:
            self.log.warning("Could not start playback, skipping...")
            self.queue.current = None
            if not self.queue.is_empty:
                await self._play(self.queue.pop())
            return

        while voice.is_connected() and (voice.is_playing() or voice.is_paused()):
            await asyncio.sleep(0.5)

        if not voice.is_connected():
            self.state = 'idle'
            self.client = None
            return

        if self.state == 'stopped' or self.state == 'paused':
            return

        if not self.queue.is_empty:
            await self._play(self.queue.pop())
        elif self.autoplay_enabled:
            await self._autoplay_next(track)
        else:
            self.log.info('Queue empty')
            self.state = 'idle'
            self.queue.current = None

    async def _autoplay_next(self, last_track: Track) -> None:
        """Fetch a recommended track via Spotify API and play it."""
        self.log.info(f'Autoplay: fetching recommendation based on {last_track.title}')

        spotify_stream = self.streams.get('spotify')
        if not spotify_stream or not spotify_stream.is_ready():
            self.log.warning("Autoplay: Spotify stream not ready, falling back to idle")
            self.state = 'idle'
            self.queue.current = None
            return

        try:
            rec_track = await asyncio.get_event_loop().run_in_executor(
                None, lambda: spotify_stream.get_recommendation(last_track.id)
            )

            if rec_track is None:
                self.log.warning("Autoplay: No recommendation found")
                self.state = 'idle'
                self.queue.current = None
                return

            rec_track.channel = last_track.channel
            self.log.info(f'Autoplay: playing {rec_track.title}')
            await self._play(rec_track)

        except Exception as e:
            self.log.error(f'Autoplay error: {str(e)}')
            self.state = 'idle'
            self.queue.current = None

    # -------------------------------------------------------------------------
    # Public: enqueueing
    # -------------------------------------------------------------------------

    async def enqueue(self, query: str, channel: Any) -> Optional[Track]:
        """Enqueue a single track (YouTube search, YouTube URL, or Spotify track URL)."""
        if 'spotify.com' in query or 'spotify:' in query:
            selected_stream_driver = 'spotify'
            self.log.info("Spotify link detected, switching driver.")
        else:
            selected_stream_driver = 'youtube'

        stream = self.streams.get(selected_stream_driver)

        if not stream:
            self.log.error(f"Stream driver '{selected_stream_driver}' not found/enabled")
            return None

        if not stream.is_ready():
            self.log.error(f"Stream '{selected_stream_driver}' is not ready")
            return None

        track = await asyncio.get_event_loop().run_in_executor(
            None, lambda: stream.get_track(query)
        )

        if track is None:
            self.log.error(f'Failed to get track for query: {query}')
            raise Exception('Failed to get track URL')

        track.channel = channel
        self.queue.enqueue(track)
        self.log.debug(f'Enqueued {track}')

        if self.state == 'idle':
            self.state = 'playing'
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
        else:
            self.log.info(f'Queued track @{self.queue.length}: {track.title} [{track.web_url}]')

        return track

    async def enqueue_collection(
        self, query: str, channel: Any
    ) -> Tuple[int, str]:
        """
        Fetch and enqueue all tracks from a Spotify album or playlist URL.

        Returns (count_enqueued, collection_name).
        count_enqueued is 0 on failure or if no playable tracks were found.

        The fetch is done in a thread executor so it doesn't block the event loop.
        Playback starts automatically after the first track is enqueued (if idle).
        """
        spotify_stream = self.streams.get('spotify')

        if not spotify_stream:
            self.log.error("Spotify stream driver not found")
            return 0, ''

        if not spotify_stream.is_ready():
            self.log.error("Spotify stream is not ready")
            return 0, ''

        self.log.info(f"Fetching collection: {query}")

        tracks, collection_name = await asyncio.get_event_loop().run_in_executor(
            None, lambda: spotify_stream.get_collection_tracks(query)
        )

        if tracks is None:
            self.log.error(f"Failed to fetch collection: {query}")
            return 0, collection_name

        if not tracks:
            self.log.warning(f"Collection returned no playable tracks: {query}")
            return 0, collection_name

        # Attach the caller's voice channel to every track before queuing
        for track in tracks:
            track.channel = channel
            self.queue.enqueue(track)

        count = len(tracks)
        self.log.info(f"Enqueued {count} tracks from '{collection_name}'")

        # Kick off playback if the player was idle
        if self.state == 'idle':
            self.state = 'playing'
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))

        return count, collection_name

    # -------------------------------------------------------------------------
    # Public: transport controls
    # -------------------------------------------------------------------------

    async def stop(self) -> None:
        """Pause playback (remembers current track for resume)."""
        if self.client is None:
            return

        if self.client[0].is_connected() and self.client[0].is_playing():
            self.paused_track = self.queue.current
            self.client[0].pause()
            self.state = 'paused'
            self.log.info(
                f'Paused playback of {self.paused_track.title if self.paused_track else "unknown"}'
            )
        else:
            self.log.debug("Called stop but no audio was playing")

    async def resume(self, channel: Any = None) -> bool:
        """
        Resume playback if it was stopped.
        Returns True if successfully resumed, False otherwise.
        """
        self.log.debug(
            f"Resume called. State: {self.state}, "
            f"Paused track: {self.paused_track}, Client: {self.client}"
        )

        if self.state == 'playing':
            self.log.debug("Already playing, nothing to resume")
            return False

        if self.paused_track and self.client is not None and self.client[0].is_connected():
            self.log.info(f"Resuming playback of {self.paused_track.title}")
            self.client[0].resume()
            self.state = 'playing'
            return True

        elif self.paused_track:
            self.log.info(f"Restarting playback of {self.paused_track.title}")
            target_channel = channel or self.paused_track.channel

            if target_channel:
                self.queue.current = self.paused_track
                track = self.paused_track
                self.paused_track = None
                asyncio.get_event_loop().create_task(self._play(track))
                return True
            else:
                self.log.error("Cannot resume: No voice channel specified")
                return False

        elif not self.queue.is_empty:
            self.log.info("Starting playback from queue")
            self.state = 'playing'
            if channel and self.queue.queue[0]:
                self.queue.queue[0].channel = channel
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
            return True

        else:
            self.log.debug("Nothing to resume")
            return False

    async def toggle_autoplay(self, channel: Any = None) -> Tuple[bool, str]:
        """Toggle autoplay on/off. Returns (new_state, message)."""
        self.autoplay_enabled = not self.autoplay_enabled
        state_str = "enabled" if self.autoplay_enabled else "disabled"
        self.log.info(f"Autoplay {state_str}")

        if self.autoplay_enabled and self.state == 'idle' and self._last_track_id:
            spotify_stream = self.streams.get('spotify')
            if spotify_stream and spotify_stream.is_ready():
                return (True, f"Autoplay {state_str}! Fetching a recommendation...")

        return (self.autoplay_enabled, f"Autoplay {state_str}.")

    async def clear(self) -> None:
        if not self.queue.is_empty:
            self.queue.queue = []

    async def skip(self) -> int:
        if self.client is None:
            return 0

        if self.state == 'paused':
            self.paused_track = None

        if self.client[0].is_connected():
            if self.client[0].is_playing():
                self.client[0].stop()

            if not self.queue.is_empty:
                self.log.info('Queue is nonempty, skipping to the next song...')
                self.state = 'playing'
                asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
                return len(self.queue)
            else:
                self.log.info('Queue is empty')
                self.queue.current = None
                self.paused_track = None
                self.state = 'idle'
                await self.client[0].disconnect()
                self.client = None
                return -1

        return -1

    # -------------------------------------------------------------------------
    # Public: info
    # -------------------------------------------------------------------------

    def list(self) -> List[Track]:
        return self.queue.queue

    def _get_track_file(self, id: str) -> str:
        if 'download_path' not in self.config:
            raise Exception('No download path configured')

        if not os.path.exists(f'{self.config["download_path"]}'):
            os.mkdir(f'{self.config["download_path"]}')

        return f'{self.config["download_path"]}/{id}.mp3'

    def _check_for_file(self, id: str) -> bool:
        return os.path.exists(self._get_track_file(id))

    def get_state(self) -> str:
        if self.state == 'paused' and self.paused_track:
            return f"Paused: {self.paused_track.title}"
        elif self.state == 'playing' and self.queue.current:
            return f"Playing: {self.queue.current.title}"
        elif not self.queue.is_empty:
            return f"Queue has {len(self.queue.queue)} songs"
        else:
            return "Idle"

    def __repr__(self) -> str:
        return f'Player[guild={self.guild}, queue={self.queue}]'
