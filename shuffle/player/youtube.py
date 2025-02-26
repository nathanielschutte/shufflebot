
import os
import logging
from typing import List, Callable
from dataclasses import dataclass

# Replace youtube_dl with yt_dlp
import yt_dlp as youtube_dl  # This allows minimal code changes

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
            'nocheckcertificate': True,
            # Add these new options for better reliability
            'geo_bypass': True,
            'ignoreerrors': True,
            'no_warnings': True
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

        # More reliable way to get the audio URL 
        formats = result.get('formats', [])
        # self.logger.debug(f'Formats: {formats}')
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        # self.logger.debug(f'Audio formats: {audio_formats}')
        
        # Select the best audio format, or fallback to the first format
        audio_url = None
        if audio_formats:
            # Sort by bitrate and pick the highest
            try:
                def _sort_key(format):
                    key = format.get('abr', 0)
                    return int(key) if key and key is not None else 0
                audio_formats.sort(key=_sort_key, reverse=True)
                audio_url = audio_formats[0]['url']
            except TypeError:
                audio_url = formats[0]['url'] if formats else None
        else:
            # Fallback to first format
            audio_url = formats[0]['url'] if formats else None
            
        if not audio_url:
            self.logger.error(f"Failed to extract audio URL for {result['id']}")
            audio_url = result['formats'][0]['url']  # Original fallback

        return Track(id=result['id'], title=result["title"], query=query, web_url=url, audio_url=audio_url)

    def is_ready(self) -> bool:
        return True