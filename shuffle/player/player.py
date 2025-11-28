# Update to Player class in shuffle/player/player.py to add resume functionality

import asyncio
import os
import discord

from typing import Any, Optional, Tuple, List

from shuffle.log import shuffle_logger

from shuffle.player.youtube import YoutubeStream
from shuffle.player.spotify import SpotifyStream

from shuffle.player.models.Queue import Queue
from shuffle.player.models.Guild import Guild
from shuffle.player.models.Track import Track

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
        # Track we were playing when paused - store it to enable resume
        self.paused_track: Optional[Track] = None 

        self.log = shuffle_logger(f'player [{self.guild.id}]')
        self.log.info(f'Created player for {self.guild} with queue {self.queue}')

    async def _play(self, track: Track) -> None:
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
            except:
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

        # --- 2. Create Synchronized Audio Source ---
        started_playing = False
        try:
            audio_source = None
            
            if track.source == 'spotify_spoof':
                self.log.debug("Starting Spotify Sync...")
                
                # A. Trigger Spotify Playback
                # We start the trigger in the background so it runs while we wait for the pipe
                if track.on_start:
                    asyncio.create_task(asyncio.to_thread(track.on_start))
                
                # B. Open the Pipe (BLOCKING WAIT)
                # This line will pause execution until Librespot actually connects
                # We use a timeout so the bot doesn't freeze forever if Spotify fails
                try:
                    self.log.debug("Waiting for audio stream...")
                    # This open() call BLOCKS until data flows
                    pipe_file = await asyncio.wait_for(
                        asyncio.to_thread(open, track.audio_url, 'rb'), 
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    self.log.error("Spotify timed out (Librespot didn't send audio)")
                    raise Exception("Spotify Timeout")

                self.log.debug("Stream received! Piping to FFmpeg...")

                # C. Create Source using the OPEN FILE
                # pipe=True tells discord.py to read from our file object, not open it again
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

            def after_playing(error):
                if error: self.log.error(f'Playback error: {error}')
                else: self.log.debug('Playback ended')

            voice.play(audio_source, after=after_playing)
            self.state = 'playing'
            started_playing = True
            self.log.debug("Playback started successfully")

        except Exception as e:
            self.log.error(f'Error creating audio source: {str(e)}')
            import traceback
            self.log.error(traceback.format_exc())

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
        else:
            self.log.info('Queue empty')
            self.state = 'idle'
            self.queue.current = None
    
    async def enqueue(self, query: str, channel: Any) -> Track:
        # 1. Detect if the user provided a Spotify Link
        if 'spotify.com' in query or 'spotify:' in query:
            selected_stream_driver = 'spotify'
            self.log.info("Spotify link detected, switching driver.")
        else:
            selected_stream_driver = 'youtube'

        # 2. Get the correct driver (YouTube or Spotify)
        stream = self.streams.get(selected_stream_driver)
        
        if not stream:
            self.log.error(f"Stream driver '{selected_stream_driver}' not found/enabled")
            return None

        if not stream.is_ready():
            self.log.error(f'Stream \'{selected_stream_driver}\' is not ready')
            return None

        # 3. Get the track info
        # run spotify.py code if driver is 'spotify'
        track = await asyncio.get_event_loop().run_in_executor(None, lambda: stream.get_track(query))
        
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

    async def stop(self) -> None:
        """
        Stop playback but remember current track for possible resume.
        This doesn't clear the queue.
        """
        if self.client is None:
            return

        if self.client[0].is_connected() and self.client[0].is_playing():
            # Remember the current track so we can resume it later
            self.paused_track = self.queue.current
            self.client[0].pause()  # Use pause instead of stop to keep the voice client connected
            self.state = 'paused'
            self.log.info(f'Paused playback of {self.paused_track.title if self.paused_track else "unknown"}')
            # Don't disconnect - keep the connection for resume functionality
        else:
            self.log.debug("Called stop but no audio was playing")

    async def resume(self, channel: Any = None) -> bool:
        """
        Resume playback if it was stopped.
        Returns True if successfully resumed, False otherwise.
        """
        self.log.debug(f"Resume called. State: {self.state}, Paused track: {self.paused_track}, Client: {self.client}")
        
        # If we're already playing, do nothing
        if self.state == 'playing':
            self.log.debug("Already playing, nothing to resume")
            return False
            
        # If we have a paused track and the client is still connected
        if self.paused_track and self.client is not None and self.client[0].is_connected():
            self.log.info(f"Resuming playback of {self.paused_track.title}")
            self.client[0].resume()  # Resume the paused playback
            self.state = 'playing'
            return True
            
        # If we have a paused track but need to reconnect
        elif self.paused_track:
            self.log.info(f"Restarting playback of {self.paused_track.title}")
            # If channel wasn't provided but we have the track's channel
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
                
        # If we have nothing to resume but have items in the queue
        elif not self.queue.is_empty:
            self.log.info("Starting playback from queue")
            self.state = 'playing'
            if channel and self.queue.queue[0]:
                self.queue.queue[0].channel = channel
            
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
            return True
            
        # Nothing to resume
        else:
            self.log.debug("Nothing to resume")
            return False


    async def clear(self) -> None:
        if not self.queue.is_empty:
            self.queue.queue = []

    
    async def skip(self) -> int:
        if self.client is None:
            return 0

        # If we're paused, clear the paused track 
        if self.state == 'paused':
            self.paused_track = None
            
        if self.client[0].is_connected():
            # Stop current playback regardless of if it's playing or paused
            if self.client[0].is_playing():
                self.client[0].stop()
            
            if not self.queue.is_empty:
                self.log.info(f'Queue is nonempty, skipping to the next song...')
                self.state = 'playing'
                asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
                
                return len(self.queue)
            else:
                self.log.info(f'Queue is empty')
                self.queue.current = None
                self.paused_track = None
                self.state = 'idle'
                await self.client[0].disconnect()
                self.client = None

                return -1

        return -1

    
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
        """Returns the current player state as a string."""
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
