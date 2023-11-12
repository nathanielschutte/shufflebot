
import os
import logging
from typing import List, Callable
from dataclasses import dataclass

import youtube_dl # type: ignore

from shuffle.log import shuffle_logger
from shuffle.player.models.Track import Track
from shuffle.player.stream import Stream

class YoutubeStream(Stream):
    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)

        self.logger = shuffle_logger('youtube')
        
        self.savedir = 'db/audio'
        self._raw_opts = {
            'outtmpl': self.savedir + '%(title)s.%(ext)s',
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'nocheckcertificate': True
        }

    def download(self, video_hash: str, path: str) -> None:
        actual_url = f'https://www.youtube.com/watch?v={video_hash}'
        self.logger.info(f'Downloading {actual_url}')
        if not os.path.exists(os.path.dirname(path)):
            os.mkdir(os.path.dirname(path))
        self._raw_opts['outtmpl'] = path
        with youtube_dl.YoutubeDL(self._raw_opts) as ydl:
            ydl.download([actual_url])

    def get_track(self, query: str) -> Track:
        # self.logger.debug(f'Getting URL for query: {query}')
        with youtube_dl.YoutubeDL(self._raw_opts) as ydl:
            result = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in result:
                result = result['entries'][0]
            # self.logger.debug(f'Got result: {result["title"]} {result["id"]} {result["webpage_url"]}')
            
        url = result['webpage_url']
        self.logger.info(f'Got URL {url} (title={result["title"]}, id={result["id"]})')

        return Track(id=result['id'], title=result["title"], query=query, web_url=url, audio_url=result['formats'][0]['url'])

    def is_ready(self) -> bool:
        return True
