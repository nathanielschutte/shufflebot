
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
        self.savedir = 'downloads/'
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

    # Get a URL from search query
    def search_url(self) -> str:
        return ''


if __name__ == '__main__':
    d = Downloader()
    video_hash = 'Htaj3o3JD8I'
    d.download(video_hash)
