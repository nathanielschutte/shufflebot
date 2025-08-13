# Player class with automatic region switching to fix connection issues
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
        
        # Working regions (based on user reports)
        self.working_regions = ['india', 'sydney', 'singapore', 'hongkong', 'japan', 'southafrica']
        self.original_regions = {}  # Store original regions to restore later
        
        # Check opus
        if not discord.opus.is_loaded():
            self.log.warning("Opus not loaded, attempting to load...")
            try:
                discord.opus.load_opus('opus')
                if discord.opus.is_loaded():
                    self.log.info("✓ Opus loaded successfully")
            except Exception as e:
                self.log.error(f"Failed to load opus: {e}")

    async def _ensure_working_region(self, channel: discord.VoiceChannel) -> str:
        """Change channel to a working region if needed"""
        try:
            current_region = channel.rtc_region
            self.log.info(f"Current voice region: {current_region or 'automatic'}")
            
            # Store original region
            if channel.id not in self.original_regions:
                self.original_regions[channel.id] = current_region
            
            # If already in a working region, do nothing
            if current_region in self.working_regions:
                self.log.info(f"Already in working region: {current_region}")
                return current_region
            
            # Try to change to a working region
            for region in self.working_regions:
                try:
                    self.log.info(f"Attempting to change region to: {region}")
                    await channel.edit(rtc_region=region)
                    self.log.info(f"✓ Successfully changed region to: {region}")
                    return region
                except discord.Forbidden:
                    self.log.warning("Bot lacks permission to change voice region")
                    self.log.info("Ask an admin to change voice region to: India, Sydney, or Singapore")
                    break
                except Exception as e:
                    self.log.debug(f"Could not change to {region}: {e}")
                    continue
                    
        except Exception as e:
            self.log.error(f"Error managing region: {e}")
        
        return channel.rtc_region

    async def _restore_original_region(self, channel: discord.VoiceChannel):
        """Restore the original region after we're done"""
        try:
            if channel.id in self.original_regions:
                original = self.original_regions[channel.id]
                if original != channel.rtc_region:
                    self.log.info(f"Restoring original region: {original or 'automatic'}")
                    await channel.edit(rtc_region=original)
                del self.original_regions[channel.id]
        except Exception as e:
            self.log.debug(f"Could not restore region: {e}")

    async def _play(self, track: Track) -> None:
        self.log.info(f'=== STARTING PLAYBACK ===')
        self.log.info(f'Track: {track.title}')
        self.log.info(f'Target channel: {track.channel.name}')

        voice = None

        # Ensure we're in a working region BEFORE connecting
        await self._ensure_working_region(track.channel)

        # Check existing client
        if self.client is not None:
            try:
                voice = self.client[0]
                if hasattr(voice, 'channel'):
                    if track.channel.id != self.client[1]:
                        self.log.info(f'Moving to new channel')
                        # Ensure new channel has working region
                        await self._ensure_working_region(track.channel)
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
                            await self._ensure_working_region(track.channel)
                            await vc.move_to(track.channel)
                    except:
                        pass
                    self.client = [voice, track.channel.id]
                    break
            
            # Create new connection
            if voice is None:
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        self.log.info(f"Connection attempt {attempt + 1}/{max_attempts}")
                        
                        # Double-check region before each attempt
                        current_region = track.channel.rtc_region
                        self.log.info(f"Connecting with region: {current_region or 'automatic'}")
                        
                        start_time = time.time()
                        voice = await track.channel.connect(timeout=30.0, reconnect=True, self_deaf=True)
                        
                        connect_time = time.time() - start_time
                        self.log.info(f"✓ Connected successfully in {connect_time:.1f}s!")
                        self.client = [voice, track.channel.id]
                        break
                        
                    except discord.ClientException as e:
                        if "4006" in str(e) or "WebSocket closed" in str(e):
                            self.log.error(f"Got 4006 error with region {track.channel.rtc_region}")
                            
                            # Try next working region
                            if attempt < max_attempts - 1:
                                next_region_idx = (self.working_regions.index(track.channel.rtc_region) + 1) % len(self.working_regions) if track.channel.rtc_region in self.working_regions else 0
                                next_region = self.working_regions[next_region_idx]
                                
                                try:
                                    self.log.info(f"Switching to {next_region} region for retry...")
                                    await track.channel.edit(rtc_region=next_region)
                                    await asyncio.sleep(2)
                                except:
                                    pass
                                    
                        elif "Already connected" in str(e):
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
                            
                    except Exception as e:
                        self.log.error(f"Failed to connect: {type(e).__name__}: {e}")
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(2)

        if voice is None:
            self.log.error("Could not establish voice connection")
            self.log.error("Please manually set voice channel region to: India, Sydney, or Singapore")
            return

        # Short wait for stability
        await asyncio.sleep(1)
        
        self.log.info("Preparing audio playback...")
        
        # Simple FFMPEG options
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        
        try:
            self.log.info("Creating audio source...")
            audio_source = discord.FFmpegPCMAudio(track.audio_url, **FFMPEG_OPTIONS)
            
            self.log.info("Starting playback...")
            voice.play(audio_source, after=lambda e: self.log.info(f'Playback ended: {e}' if e else 'Playback ended normally'))
            
            self.state = 'playing'
            self.log.info("✓✓✓ PLAYBACK STARTED SUCCESSFULLY ✓✓✓")
            
        except discord.ClientException as e:
            if "Not connected" in str(e):
                self.log.error("Still not connected despite successful connection")
                self.log.error("This is a discord.py bug with this region")
            else:
                self.log.error(f"Playback error: {e}")
            return
            
        except Exception as e:
            self.log.error(f'Failed to play: {type(e).__name__}: {e}')
            return

        # Monitor playback
        self.log.info("Monitoring playback...")
        check_count = 0
        
        while voice and (voice.is_playing() or voice.is_paused()):
            if check_count % 20 == 0:  # Log every 10 seconds
                self.log.debug(f"Still playing... (check {check_count})")
            check_count += 1
            await asyncio.sleep(0.5)
            
            if self.state in ['stopped', 'idle']:
                break
                
        self.log.info(f'Playback finished for {track.title}')

        # Continue with queue
        if self.state == 'stopped' or self.state == 'paused':
            self.log.info(f'State is {self.state}, not continuing')
            return

        if not self.queue.is_empty and self.state == 'playing':
            self.log.info(f'Playing next song ({len(self.queue.queue)} in queue)...')
            await self._play(self.queue.pop())
        else:
            self.log.info('Queue empty, disconnecting...')
            self.queue.current = None
            self.paused_track = None
            self.state = 'idle'
            
            if voice:
                try:
                    # Restore original region before disconnecting
                    if voice.channel:
                        await self._restore_original_region(voice.channel)
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
            if voice.is_playing():
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
                voice.resume()
                self.state = 'playing'
                self.log.info("Resumed playback")
                return True
            except Exception as e:
                self.log.error(f"Error resuming: {e}")
                
        if self.paused_track:
            self.log.info(f"Restarting: {self.paused_track.title}")
            target_channel = channel or self.paused_track.channel
            
            if target_channel:
                track = self.paused_track
                self.paused_track = None
                self.state = 'playing'
                asyncio.get_event_loop().create_task(self._play(track))
                return True
                
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
                
            if voice.is_playing() or voice.is_paused():
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
                
                # Restore region before disconnecting
                if voice.channel:
                    await self._restore_original_region(voice.channel)
                    
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