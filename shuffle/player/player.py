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
            try:
                # Check if the client is still valid and connected
                if self.client[0].is_connected():
                    if track.channel.id != self.client[1]:
                        self.log.debug(f'Moving from old channel {self.client[1]} to request channel {track.channel.id}')
                        await self.client[0].move_to(track.channel)
                        voice = self.client[0]
                        self.client[1] = track.channel.id
                    else:
                        voice = self.client[0]
                        self.log.debug("Using existing voice client")
                else:
                    # Client exists but not connected, clean it up
                    self.log.debug("Client exists but not connected, cleaning up")
                    self.client = None
            except Exception as e:
                self.log.error(f"Error checking existing client: {e}")
                # Clean up invalid client
                try:
                    if self.client and self.client[0]:
                        await self.client[0].disconnect(force=True)
                except:
                    pass
                self.client = None
        
        # Need a new voice client
        if voice is None:
            # First check if bot is already in a voice channel in this guild
            if self.bot and hasattr(self.bot, 'voice_clients'):
                for vc in self.bot.voice_clients:
                    if vc.guild.id == self.guild.id:
                        self.log.debug("Found existing voice client in guild")
                        try:
                            if vc.channel.id != track.channel.id:
                                await vc.move_to(track.channel)
                            voice = vc
                            self.client = [voice, track.channel.id]
                            break
                        except Exception as e:
                            self.log.error(f"Error reusing voice client: {e}")
                            try:
                                await vc.disconnect(force=True)
                            except:
                                pass
            
            # If still no voice client, create new one
            if voice is None:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.log.debug(f"Attempting to connect to voice channel (attempt {attempt + 1}/{max_retries})")
                        
                        # Add timeout and reconnect parameters
                        voice = await track.channel.connect(timeout=60.0, reconnect=True)
                        self.client = [voice, track.channel.id]
                        self.log.debug("Successfully connected to voice channel")
                        break
                        
                    except discord.ClientException as e:
                        if "Already connected" in str(e):
                            self.log.warning("Already connected to voice channel, attempting to find it")
                            # Try to find the existing connection
                            for vc in self.bot.voice_clients:
                                if vc.guild.id == self.guild.id:
                                    voice = vc
                                    self.client = [voice, vc.channel.id]
                                    if vc.channel.id != track.channel.id:
                                        await vc.move_to(track.channel)
                                        self.client[1] = track.channel.id
                                    break
                            if voice:
                                break
                        else:
                            raise
                            
                    except IndexError as e:
                        self.log.error(f"IndexError connecting to voice (attempt {attempt + 1}): {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)  # Wait longer between retries
                        else:
                            self.log.error("Failed to connect after all retries - Discord voice servers may be having issues")
                            
                    except Exception as e:
                        self.log.error(f"Unexpected error connecting to voice: {type(e).__name__}: {e}")
                        import traceback
                        self.log.error(traceback.format_exc())
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)

        if voice is None:
            self.log.error("Failed to establish voice connection")
            # Clean up
            self.queue.current = None
            self.paused_track = None
            self.state = 'idle'
            
            # Try next in queue if available
            if not self.queue.is_empty:
                self.log.info("Trying next track in queue...")
                await asyncio.sleep(3)  # Give Discord more time
                asyncio.create_task(self._play(self.queue.pop()))
            return

        # Ensure voice client is ready
        await asyncio.sleep(0.5)  # Small delay to ensure connection is stable
        
        # Simple FFMPEG options that work reliably
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        
        self.log.debug(f'Attempting to play with audio URL: {track.audio_url[:100]}...')
        
        # Track if we successfully started playing
        started_playing = False
        
        try:
            self.log.debug("Creating FFmpegPCMAudio instance...")
            
            # Create the audio source
            audio_source = discord.FFmpegPCMAudio(
                track.audio_url, 
                **FFMPEG_OPTIONS
            )
            
            self.log.debug("Created FFmpegPCMAudio instance successfully")
            
            # Create an error callback
            def after_playing(error):
                if error:
                    self.log.error(f'Playback error: {error}')
                else:
                    self.log.debug('Playback ended normally')
            
            # Start playing
            voice.play(audio_source, after=after_playing)
            self.state = 'playing'
            started_playing = True
            self.log.debug("Playback started successfully")
            
        except Exception as e:
            self.log.error(f'Error creating audio source: {str(e)}')
            import traceback
            self.log.error(traceback.format_exc())
            
            # Try a simpler approach
            if not started_playing:
                try:
                    self.log.info('Attempting minimal FFmpeg options')
                    audio_source = discord.FFmpegPCMAudio(track.audio_url)
                    voice.play(audio_source)
                    self.state = 'playing'
                    started_playing = True
                    self.log.debug("Minimal playback started")
                except Exception as e2:
                    self.log.error(f'Minimal approach also failed: {str(e2)}')

        # If we couldn't start playing at all, skip to next track
        if not started_playing:
            self.queue.current = None
            self.paused_track = None
            
            # Don't disconnect - might be useful for next track
            if not self.queue.is_empty and self.state != 'stopped':
                self.log.debug('Skipping to next track...')
                await asyncio.sleep(1)
                asyncio.create_task(self._play(self.queue.pop()))
                return
            else:
                self.log.debug('No more tracks, disconnecting')
                self.state = 'idle'
                if voice:
                    try:
                        await voice.disconnect()
                    except:
                        pass
                self.client = None
                return

        # Wait for the song to finish playing
        while voice.is_connected() and (voice.is_playing() or voice.is_paused()):
            await asyncio.sleep(0.5)
            
        self.log.debug(f'Done playing {track.title}')

        # Check why we stopped
        if not voice.is_connected():
            self.log.debug('Voice disconnected during playback')
            self.state = 'idle'
            self.client = None
            return
            
        if self.state == 'stopped' or self.state == 'paused':
            self.log.debug(f'Playback {self.state}, not continuing queue')
            return

        # Continue with queue if available
        if not self.queue.is_empty and self.state == 'playing':
            self.log.debug(f'Playing next song from queue ({len(self.queue.queue)} remaining)...')
            await self._play(self.queue.pop())
        else:
            self.log.info('Queue empty, disconnecting')
            self.queue.current = None
            self.paused_track = None
            self.state = 'idle'
            try:
                await voice.disconnect()
            except:
                pass
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
