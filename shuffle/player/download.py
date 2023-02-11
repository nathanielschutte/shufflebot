
import os
import logging
from typing import List, Callable
from dataclasses import dataclass

import youtube_dl

@dataclass
class DownloadOpts:
    format = 'worstaudio/worst'
    postprocessors = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
    prefer_ffmpeg = True
    keepvideo = False

class Downloader:
    def __init__(self) -> None:
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] |   %(message)s')
        console_handle = logging.StreamHandler()
        console_handle.setFormatter(formatter)
        self.logger.addHandler(console_handle)
        
        self.savedir = 'db/audio'
        self._raw_opts = {
            'outtmpl': self.savedir + '%(title)s.%(ext)s',
            'format': 'worstaudio/worst',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'nocheckcertificate': True
        }

        # self._opts = DownloadOpts()

    def download(self, video_hash: str) -> None:
        actual_url = f'https://www.youtube.com/watch?v={video_hash}'
        self.logger.info(f'Downloading {actual_url}')
        if not os.path.exists(self.savedir):
            os.mkdir(self.savedir)
        self._raw_opts['outtmpl'] = os.path.join(self.savedir, f'{video_hash}.mp3')
        with youtube_dl.YoutubeDL(self._raw_opts) as ydl:
            ydl.download([actual_url])

    def get_url(self, query: str) -> str:
        self.logger.info(f'Getting URL for query: {query}')
        
        with youtube_dl.YoutubeDL(self._raw_opts) as ydl:
            result = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in result:
                result = result['entries'][0]
            self.logger.debug(f'Got result: {result["title"]} {result["id"]} {result["webpage_url"]}')
            
        url = result['webpage_url']
        self.logger.debug(f'Got URL {url} (id={result["id"]})')
        return url


    # Get a URL from search query
    def search_url(self) -> str:
        return ''


if __name__ == '__main__':
    d = Downloader()
    video_hash = 'Htaj3o3JD8I'
    d.download(video_hash)
