
import os
import logging
from typing import List, Callable
from dataclasses import dataclass
import random
import string

import yt_dlp as youtube_dl

from shuffle.log import shuffle_logger
from shuffle.player.models.Track import Track
from shuffle.player.stream import Stream
from shuffle.constants import PROJECT_ROOT

class YoutubeStream(Stream):
    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)

        self.logger = shuffle_logger('youtube')

        # user_agents = [
        #     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        #     'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        #     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        #     'Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
        #     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        # ]

        proxy_list_path = os.path.join(PROJECT_ROOT, 'config/proxies.txt')
        self.proxies = []

        # if os.path.exists(proxy_list_path):
        #     with open(proxy_list_path, 'r') as f:
        #         self.proxies = [line.strip() for line in f if line.strip()]
        #     self.logger.info(f"Loaded {len(self.proxies)} proxies")
        # else:
        #     self.logger.warning(f"Proxy list not found at {proxy_list_path}")
        
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
            # 'user_agent': random.choice(user_agents),
            'referer': 'https://www.youtube.com/',
            'geo_bypass': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'extractor_retries': 10,
            'socket_timeout': 30,
            'concurrent_fragment_downloads': 5,
            'downloader_options': {
                'http': {
                    'chunk_size': 10485760,  # 10MB
                }
            },
            'client_identifier': ''.join(random.choice(string.ascii_lowercase) for i in range(8)),
            'throttledratelimit': 100000,  # Increase rate limit
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
        # self._raw_opts['user_agent'] = random.choice([
        #     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        #     'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        #     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        # ])


        url = None
        attempt = 1
        while not url and attempt <= 3:
            if self.proxies:
                proxy = random.choice(self.proxies)
                self._raw_opts['proxy'] = proxy
                self.logger.debug(f"Using proxy: {proxy}")
            try:
                with youtube_dl.YoutubeDL(self._raw_opts) as ydl:
                    result = ydl.extract_info(f"ytsearch:{query}", download=False)
                    if 'entries' in result:
                        result = result['entries'][0]
                    url = result['webpage_url']
                    break
            except Exception as e:
                self.logger.error(f"Error with initial search: {str(e)}")
                attempt += 1
                self.logger.info(f"Retrying search (attempt {attempt})")



        if not url:
            self.logger.error(f"Failed to extract URL for {query}")
            return None

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