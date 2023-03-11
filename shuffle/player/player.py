
# Player for a single guild

import asyncio
import os
import discord

from typing import Any

from shuffle.log import shuffle_logger

from shuffle.player.youtube import Downloader

from shuffle.player.models.Queue import Queue
from shuffle.player.models.Guild import Guild
from shuffle.player.models.Track import Track

class Player:
    def __init__(self, guild_id: int, config: dict, bot: Any) -> None:
        self.guild = Guild(guild_id)
        self.queue = Queue()
        self.downloader = Downloader()
        self.config = config
        self.bot = bot

        self.state = 'idle'

        self.client = None

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
            self.client = voice, track.channel.id

        assert voice is not None
        
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        voice.play(discord.FFmpegPCMAudio(track.audio_url, **FFMPEG_OPTIONS))
        
        play_counter = 0
        while voice.is_connected() and voice.is_playing():
            await asyncio.sleep(1)
            play_counter += 1
            if play_counter > 1000:
                self.log.warn(f'Track timeout after 1000 seconds: {track.id}')
                break
        self.log.debug(f'Done playing {track.title} [{track.web_url}]')

        if not voice.is_connected():
            self.queue.current = None
            self.client = None

        if not self.queue.is_empty and self.state == 'playing':
            self.log.debug(f'Queue is nonempty, playing next song...')
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
        else:
            self.queue.current = None
            await voice.disconnect()
            self.client = None
        
    
    async def enqueue(self, query: str, channel: Any) -> Track:
        track = await asyncio.get_event_loop().run_in_executor(None, lambda: self.downloader.get_track(query))
        track.channel = channel
        self.queue.enqueue(track)
        self.log.debug(f'Enqueued {track}')

        # if not self._check_for_file(track.id):
        #     self.log.debug(f'Downloading {track.id}')
        #     await asyncio.get_event_loop().run_in_executor(None, lambda: self.downloader.download(track.id, self._get_track_file(track.id)))
        # else:
        #     self.log.debug(f'Already downloaded {track.id}')

        # if not self._check_for_file(track.id):
        #     self.log.error(f'Could not download {track.id}')
        #     return

        if not self.queue.is_playing:
            self.state = 'playing'
            asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
        else:
            self.log.info(f'Queued track @{self.queue.length}: {track.title} [{track.web_url}]')

        return track

    async def stop(self) -> None:
        if self.client is None:
            return

        self.state = 'stopped'

        if self.client[0].is_connected() and self.client[0].is_playing():
            self.client[0].stop()

        await self.client[0].disconnect()


    async def clear(self) -> None:
        if not self.queue.is_empty:
            self.queue.queue = []

    
    async def skip(self) -> int:
        if self.client is None:
            return

        if self.client[0].is_connected() and self.client[0].is_playing():
            self.client[0].stop()

            if not self.queue.is_empty:
                self.log.info(f'Queue is nonempty, skipping to the next song...')
                self.state = 'playing'
                asyncio.get_event_loop().create_task(self._play(self.queue.pop()))
                
                return len(self.queue)
            else:
                self.log.info(f'Queue is empty')
                self.queue.current = None
                await self.client[0].disconnect()
                self.client = None

                return -1

        return None

    
    def list(self) -> None:
        return self.queue.queue

    
    def _get_track_file(self, id: str) -> str:
        if 'download_path' not in self.config:
            raise Exception('No download path configured')

        if not os.path.exists(f'{self.config["download_path"]}'):
            os.mkdir(f'{self.config["download_path"]}')

        return f'{self.config["download_path"]}/{id}.mp3'


    def _check_for_file(self, id: str) -> bool:
        return os.path.exists(self._get_track_file(id))

    def __repr__(self) -> str:
        return f'Player[guild={self.guild}, queue={self.queue}]'
