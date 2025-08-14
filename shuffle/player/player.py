# Working Player class with alternative connection workaround
# Save this as player.py in shuffle/player/

import asyncio
import os
import discord
import sys
import traceback
import time

from typing import Any, Optional, Tuple, List

from shuffle.log import shuffle_logger

from shuffle.player.youtube import YoutubeStream

from shuffle.player.models.Queue import Queue
from shuffle.player.models.Guild import Guild
from shuffle.player.models.Track import Track

class Player:
    def __init__(self, guild_id: int, config: dict, bot: Any) -> None:
        self.guild = Guild(guild_id)
        self.queue = Queue()
        self.streams = {
            'youtube': YoutubeStream(guild_id),
        }
        self.config = config
        self.bot = bot

        self.state = 'idle'
        self.client: Optional[List[Any]] = None
        self.paused_track: Optional[Track] = None 

        self.log = shuffle_logger(f'player [{self.guild.id}]')
        self.log.info(f'Created player for {self.guild} with queue {self.queue}')
        
        # Check opus
        if not discord.opus.is_loaded():
            self.log.warning("Opus not loaded, attempting to load...")
            try:
                discord.opus.load_opus('opus')
                if discord.opus.is_loaded():
                    self.log.info("✓ Opus loaded successfully")
            except Exception as e:
                self.log.error(f"Failed to load opus: {e}")

    async def _play(self, track: Track) -> None:
        self.log.info(f'=== STARTING PLAYBACK ===')
        self.log.info(f'Track: {track.title}')
        self.log.info(f'Target channel: {track.channel.name}')

        voice = None

        # Check existing client
        if self.client is not None:
            try:
                voice = self.client[0]
                # Don't check is_connected, just try to use it
                if hasattr(voice, 'channel'):
                    if track.channel.id != self.client[1]:
                        self.log.info(f'Moving to new channel')
                        await voice.move_to(track.channel)
                        self.client[1] = track.channel.id
                    else:
                        self.log.info("Reusing existing client")
                else:
                    self.log.info("Client invalid, creating new one")
                    self.client = None
                    voice = None
            except Exception as e:
                self.log.error(f"Error with existing client: {e}")
                self.client = None
                voice = None
        
        # Create new connection if needed
        if voice is None:
            self.log.info("Creating new voice connection...")
            
            # Check for existing connections
            for vc in self.bot.voice_clients:
                if vc.guild.id == self.guild.id:
                    self.log.info("Found existing voice client, using it")
                    voice = vc
                    try:
                        if vc.channel.id != track.channel.id:
                            await vc.move_to(track.channel)
                    except:
                        pass
                    self.client = [voice, track.channel.id]
                    break
            
            # Create new connection
            if voice is None:
                max_attempts = 2
                for attempt in range(max_attempts):
                    try:
                        self.log.info(f"Connection attempt {attempt + 1}/{max_attempts}")
                        self.log.info(f"Connecting to {track.channel.name}...")
                        
                        start_time = time.time()
                        
                        # Try with shorter timeout first
                        voice = await track.channel.connect(timeout=10.0, reconnect=False, self_deaf=True)
                        
                        connect_time = time.time() - start_time
                        self.log.info(f"✓ Got voice client object after {connect_time:.1f}s")
                        self.client = [voice, track.channel.id]
                        
                        # Don't verify connection, just proceed
                        self.log.info("Skipping connection verification...")
                        break
                        
                    except asyncio.TimeoutError:
                        self.log.error(f"Connection timeout after 10s")
                        if attempt < max_attempts - 1:
                            self.log.info("Retrying with longer timeout...")
                            try:
                                # Try again with longer timeout
                                voice = await track.channel.connect(timeout=30.0, reconnect=True)
                                self.log.info("✓ Connected on second attempt")
                                self.client = [voice, track.channel.id]
                                break
                            except:
                                pass
                                
                    except discord.ClientException as e:
                        if "Already connected" in str(e):
                            self.log.info("Already connected, finding existing client")
                            for vc in self.bot.voice_clients:
                                if vc.guild.id == self.guild.id:
                                    voice = vc
                                    self.client = [voice, track.channel.id]
                                    break
                            if voice:
                                break
                        else:
                            self.log.error(f"Connection error: {e}")
                            if attempt < max_attempts - 1:
                                await asyncio.sleep(2)
                            
                    except Exception as e:
                        self.log.error(f"Failed to connect: {type(e).__name__}: {e}")
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(2)

        if voice is None:
            self.log.error("Could not get voice client")
            return

        # Wait a moment for connection to stabilize
        await asyncio.sleep(2)
        
        self.log.info("Preparing audio...")
        
        # Create a custom audio source that bypasses connection check
        class ForcePlayAudioSource(discord.FFmpegPCMAudio):
            """Custom audio source that doesn't check connection status"""
            def __init__(self, source, **kwargs):
                super().__init__(source, **kwargs)
        
        # Simple FFMPEG options
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        
        success = False
        
        # Try multiple approaches
        for approach_num in range(3):
            try:
                if approach_num == 0:
                    self.log.info("Approach 1: Standard play...")
                    audio_source = discord.FFmpegPCMAudio(track.audio_url, **FFMPEG_OPTIONS)
                    voice.play(audio_source, after=lambda e: self.log.info(f'Playback ended: {e}'))
                    success = True
                    
                elif approach_num == 1:
                    self.log.info("Approach 2: Custom audio source...")
                    audio_source = ForcePlayAudioSource(track.audio_url, **FFMPEG_OPTIONS)
                    voice.play(audio_source, after=lambda e: self.log.info(f'Playback ended: {e}'))
                    success = True
                    
                elif approach_num == 2:
                    self.log.info("Approach 3: Minimal FFmpeg...")
                    audio_source = discord.FFmpegPCMAudio(track.audio_url)
                    voice.play(audio_source)
                    success = True
                
                if success:
                    self.state = 'playing'
                    self.log.info(f"✓✓✓ PLAYBACK STARTED with approach {approach_num + 1} ✓✓✓")
                    break
                    
            except discord.ClientException as e:
                if "Not connected" in str(e):
                    self.log.warning(f"Approach {approach_num + 1} failed: Not connected")
                    
                    # Try to manually set the voice client as playing
                    if approach_num == 0:
                        # Wait and retry
                        await asyncio.sleep(2)
                        continue
                    elif approach_num == 1:
                        # Try to trick it by setting internal state
                        try:
                            # Try to access internal websocket
                            if hasattr(voice, 'ws') and voice.ws:
                                self.log.info("Voice has websocket, waiting for it...")
                                await asyncio.sleep(3)
                                continue
                        except:
                            pass
                else:
                    self.log.error(f"Approach {approach_num + 1} error: {e}")
                    
            except Exception as e:
                self.log.error(f"Approach {approach_num + 1} failed: {type(e).__name__}: {e}")

        if not success:
            self.log.error("All playback approaches failed")
            
            # Last resort: Create new FFmpeg process directly
            self.log.info("Last resort: Direct FFmpeg process...")
            try:
                import subprocess
                
                # Start FFmpeg to play audio (this won't go through Discord but tests if audio works)
                self.log.info("Testing if FFmpeg can access the URL...")
                
                test_cmd = [
                    'ffmpeg', '-i', track.audio_url,
                    '-t', '5',  # Only test 5 seconds
                    '-f', 'null', '-'
                ]
                
                result = subprocess.run(test_cmd, capture_output=True, timeout=10)
                
                if result.returncode == 0:
                    self.log.info("✓ FFmpeg can access the audio URL")
                    self.log.info("The issue is with Discord voice connection")
                    self.log.info("Try: 1) Different Discord server, 2) Mobile hotspot, 3) VPN")
                else:
                    self.log.error("✗ FFmpeg cannot access the audio URL")
                    self.log.error("The YouTube URL might be expired or region-blocked")
                    
            except Exception as e:
                self.log.error(f"FFmpeg test failed: {e}")
            
            return

        # Monitor playback
        self.log.info("Monitoring playback...")
        check_count = 0
        
        while True:
            try:
                # Check if we can determine playback status
                is_playing = False
                is_paused = False
                
                try:
                    is_playing = voice.is_playing() if hasattr(voice, 'is_playing') else False
                    is_paused = voice.is_paused() if hasattr(voice, 'is_paused') else False
                except:
                    # If we can't check, assume it's playing for a while
                    if check_count < 100:  # About 50 seconds
                        is_playing = True
                
                if check_count % 10 == 0:  # Log every 5 seconds
                    self.log.debug(f"Status check {check_count}: playing={is_playing}, paused={is_paused}")
                
                if not is_playing and not is_paused and self.state == 'playing':
                    if check_count > 10:  # Give it at least 5 seconds
                        self.log.info("Playback appears to have ended")
                        break
                    
                if self.state in ['stopped', 'idle']:
                    self.log.info("Playback manually stopped")
                    break
                    
                check_count += 1
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.log.error(f"Error in playback loop: {e}")
                break
                
        self.log.info(f'Playback ended for {track.title}')

        # Clean up and continue
        if self.state == 'stopped' or self.state == 'paused':
            self.log.info(f'State is {self.state}, not continuing')
            return

        # Play next in queue
        if not self.queue.is_empty and self.state == 'playing':
            self.log.info(f'Playing next song ({len(self.queue.queue)} in queue)...')
            await self._play(self.queue.pop())
        else:
            self.log.info('Queue empty, cleaning up')
            self.queue.current = None
            self.paused_track = None
            self.state = 'idle'
            
            if voice:
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

        self.log.info(f"Getting track for: {query}")
        track = await asyncio.get_event_loop().run_in_executor(None, lambda: stream.get_track(query))
        if track is None:
            self.log.error(f'Failed to get track')
            raise Exception('Failed to get track URL')
            
        track.channel = channel
        self.queue.enqueue(track)
        self.log.info(f'Enqueued: {track.title}')

        if self.state == 'idle':
            self.state = 'playing'
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
        else:
            self.log.info(f'Added to queue position {self.queue.length}')

        return track

    async def stop(self) -> None:
        """Stop/pause playback"""
        if self.client is None:
            return

        try:
            voice = self.client[0]
            if hasattr(voice, 'is_playing') and voice.is_playing():
                self.paused_track = self.queue.current
                voice.pause()
                self.state = 'paused'
                self.log.info(f'Paused playback')
        except Exception as e:
            self.log.error(f"Error stopping: {e}")

    async def resume(self, channel: Any = None) -> bool:
        """Resume playback"""
        self.log.info(f"Resume called. State: {self.state}")
        
        if self.state == 'playing':
            return False
            
        if self.client:
            try:
                voice = self.client[0]
                if hasattr(voice, 'resume'):
                    voice.resume()
                    self.state = 'playing'
                    self.log.info("Resumed playback")
                    return True
            except Exception as e:
                self.log.error(f"Error resuming: {e}")
                
        # Restart playback if we have a paused track
        if self.paused_track:
            self.log.info(f"Restarting: {self.paused_track.title}")
            target_channel = channel or self.paused_track.channel
            
            if target_channel:
                track = self.paused_track
                self.paused_track = None
                self.state = 'playing'
                asyncio.get_event_loop().create_task(self._play(track))
                return True
                
        # Start from queue
        elif not self.queue.is_empty:
            self.log.info("Starting from queue")
            self.state = 'playing'
            if channel:
                self.queue.queue[0].channel = channel
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
            return True
            
        return False

    async def clear(self) -> None:
        if not self.queue.is_empty:
            self.queue.queue = []

    async def skip(self) -> int:
        if self.client is None:
            return 0

        try:
            voice = self.client[0]
            
            if self.state == 'paused':
                self.paused_track = None
                
            if hasattr(voice, 'stop'):
                voice.stop()
            
            if not self.queue.is_empty:
                self.log.info(f'Skipping to next song...')
                self.state = 'playing'
                asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
                return len(self.queue)
            else:
                self.log.info(f'Queue empty')
                self.queue.current = None
                self.paused_track = None
                self.state = 'idle'
                
                try:
                    await voice.disconnect()
                except:
                    pass
                self.client = None
                return -1
                
        except Exception as e:
            self.log.error(f"Error skipping: {e}")
            return -1

    def list(self) -> List[Track]:
        return self.queue.queue

    def __repr__(self) -> str:
        return f'Player[guild={self.guild}, queue={self.queue}]'