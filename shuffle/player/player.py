
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
    def __init__(self, guild_id: int, config: dict) -> None:
        self.guild = Guild(guild_id)
        self.queue = Queue()
        self.downloader = Downloader()
        self.config = config

        self.log = shuffle_logger(f'player [guild={self.guild.id}]')
        self.log.debug(f'Created player for {self.guild} with queue {self.queue}')

    async def _play(self, track: Track) -> None:
        self.log.debug(f'Playing {track}')

        voice = await track.channel.connect()
        voice.play(discord.FFmpegPCMAudio(self._get_track_file(track.id)))
        
        play_counter = 0
        while voice.is_playing():
            await asyncio.sleep(1)
            play_counter += 1
            if play_counter > 1000:
                self.log.error(f'Track timeout out after 1000 seconds: {track.id}')
                break

        self.log.debug(f'Done playing {track}')

        if not self.queue.is_empty:
            await self._play(self.queue.pop())
        else:
            self.queue.current = None
        
        await voice.disconnect()
        
    
    async def enqueue(self, query: str, channel: Any) -> None:
        track = await asyncio.get_event_loop().run_in_executor(None, lambda: self.downloader.get_track(query))
        track.channel = channel
        self.queue.enqueue(track)
        self.log.debug(f'Enqueued {track}')

        if not self._check_for_file(track.id):
            self.log.debug(f'Downloading {track}')
            await asyncio.get_event_loop().run_in_executor(None, lambda: self.downloader.download(track.id, self._get_track_file(track.id)))

        if not self._check_for_file(track.id):
            self.log.error(f'Could not download {track}')
            return

        if not self.queue.is_playing:
            await self._play(self.queue.pop())

    
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
