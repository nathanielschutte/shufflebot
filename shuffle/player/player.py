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
            # 'spotify': SpotifyStream(guild_id)
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

        voice = None

        # Check if existing voice client is in the correct channel
        if self.client is not None:
            if track.channel.id != self.client[1]:
                self.log.debug(f'Moving from old channel {self.client[1]} to request channel {track.channel.id}')
                await self.client[0].move_to(track.channel.id)
                voice = self.client[0]
                self.client[1] = track.channel.id
            else:
                voice = self.client[0]
        
        # Need a new voice client
        if voice is None:
            voice = await track.channel.connect()
            self.client = [voice, track.channel.id]

        assert voice is not None
        
        # More robust FFMPEG options with extensive error handling and reconnection capabilities
        FFMPEG_OPTIONS = {
            'before_options': '-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 15 -timeout 10000000',
            'options': '-vn -dn -sn -threads 4 -af "volume=0.5"'
        }
        
        self.log.debug(f'Attempting to play with audio URL: {track.audio_url[:100]}...')
        
        try:
            self.log.debug("Creating FFmpegPCMAudio instance...")
            audio_source = discord.FFmpegPCMAudio(track.audio_url, **FFMPEG_OPTIONS)
            self.log.debug("Created FFmpegPCMAudio instance successfully")
            
            # Add a volume transformer to prevent potential clipping/distortion
            audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.5)
            
            self.log.debug("Starting playback...")
            voice.play(audio_source)
            self.log.debug("Playback started successfully")
            self.state = 'playing'
        except Exception as e:
            self.log.error(f'Error in playback: {str(e)}')
            # Try with simplified options as a fallback
            try:
                self.log.info(f'Attempting fallback with simplified options')
                FALLBACK_OPTIONS = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1',
                    'options': '-vn'
                }
                audio_source = discord.FFmpegPCMAudio(track.audio_url, **FALLBACK_OPTIONS)
                voice.play(audio_source)
                self.log.debug("Fallback playback started successfully")
                self.state = 'playing'
            except Exception as e2:
                self.log.error(f'Fallback also failed: {str(e2)}')
                self.queue.current = None
                self.paused_track = None
                if not self.queue.is_empty and self.state != 'stopped':
                    self.log.debug(f'Skipping problematic track, trying next song...')
                    asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
                    return
                else:
                    self.log.debug(f'No more tracks to play, disconnecting')
                    self.state = 'idle'
                    await voice.disconnect()
                    self.client = None
                    return
    
        play_counter = 0
        while voice.is_connected() and voice.is_playing():
            await asyncio.sleep(1)
            play_counter += 1
            if play_counter > 1000:
                self.log.warn(f'Track timeout after 1000 seconds: {track.id}')
                break
        self.log.debug(f'Done playing {track.title} [{track.web_url}]')

        # If we disconnected or the bot was stopped, don't continue with the queue
        if not voice.is_connected() or self.state == 'stopped' or self.state == 'paused':
            return

        if not self.queue.is_empty and self.state == 'playing':
            self.log.debug(f'Queue is nonempty, playing next song...')
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
        else:
            self.queue.current = None
            self.paused_track = None
            self.state = 'idle'
            await voice.disconnect()
            self.client = None
    
    async def enqueue(self, query: str, channel: Any) -> Track:
        selected_stream_driver = 'youtube'
        stream = self.streams[selected_stream_driver]

        if not stream.is_ready():
            self.log.error(f'Stream \'{selected_stream_driver}\' is not ready')
            return None

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
