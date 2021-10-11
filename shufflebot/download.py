
# Download videos

from __future__ import unicode_literals
import youtube_dl

class Downloader:
    """YouTube mp3 downloader"""

    def __init__(self, savedir=None) -> None:
        self.savedir = savedir
        self.download_status = None

        self.opts = {
            'outtmpl': '%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [self.status_hook],
        }
        self.ydl = youtube_dl.YoutubeDL(self.opts)

    def check_link(self, link):
        with self.ydl:
            result = self.ydl.extract_info(link, download=False)
            if 'entries' in result:
                vid = result['entries'][0] # first entry of multiple
            else:
                vid = result

    def status_hook(self, d):
        if 'status' in d:
            self.download_status = d['status']
        if d['status'] == 'downloading':
            print('[downloader]: downloading...')
        elif d['status'] == 'finished':
            print('[downloader]: finished downloading, converting...')
        elif d['status'] == 'error':
            print('[downloader]: error')