
# Download videos

from __future__ import unicode_literals
from validators.utils import ValidationFailure
import youtube_dl
import validators
import os, shutil

from .exceptions import DownloadException 

# test: https://www.youtube.com/watch?v=oR4uKcvQbGQ

class Downloader:
    """YouTube mp3 downloader"""

    def __init__(self, savedir, codec) -> None:

        if savedir is not None and savedir[-1] != '/':
            savedir += '/'

        if codec[0] == '.':
            codec = codec[1:]

        self.savedir = savedir
        self.download_status = None

        self.opts = {
            'outtmpl': self.savedir + '%(title)s.%(ext)s',
            'format': 'worstaudio/worst',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': '192',
            }],
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'progress_hooks': [self.__status_hook],
        }

    # Find out what video title is associated with the given URL or query string
    async def get_title(self, string) -> str:
        
        # determine if URL or query
        isUrl = self.__check_url_vs_query(string)
        print(f'{isUrl=}')

        # extract info no download
        with youtube_dl.YoutubeDL(self.opts) as ydl:
            if isUrl:
                try:
                    result = ydl.extract_info(string, download=False)

                    # handle playlists
                    if 'entries' in result:
                        result = result['entries'][0]

                    print(f'URL RESULT: {result["title"]} {result["id"]}')
                    return result['title'], result['id']

                except Exception as e:
                    raise DownloadException(e)
            else:
                try:
                    result = ydl.extract_info(f"ytsearch:{string}", download=False)
                    if 'entries' in result:
                        result = result['entries'][0]
                    
                    print(f'QUERY RESULT: {result["title"]} {result["id"]}')
                    return result['title'], result['id']

                except Exception as e:
                    raise DownloadException(e)

    def download_url(self, url):
        self.__download(url=url)

    def download_query(self, query):
        self.__download(query=query)

    def download_video(self, string):
        isUrl = self.__check_url_vs_query(string)
        if isUrl:
            self.__download(url=string)
        else:
            self.__download(query=string)
    
    def __download(self, url=None, query=None) -> str:
        if url is not None:
            with youtube_dl.YoutubeDL(self.opts) as ydl:
                ydl.download([url])
                return
        elif query is not None:
            pass

    # Is the string a URL
    def __check_url_vs_query(self, string):
        string = string.strip()
        
        # multiple words passed but maybe the first one is still a URL
        if string.find(' ') != -1:
            return self.__check_url_vs_query(string[:string.find(' ')])
        
        # just one word, see if it's a URL
        else:
            valid = validators.url(string)
            if valid is True:
                return True
            else:
                return False

    # Download status events
    def __status_hook(self, d):
        if 'status' in d:
            self.download_status = d['status']

        if d['status'] == 'downloading':
            print('[downloader]: downloading...')

        elif d['status'] == 'finished':
            print('[downloader]: finished downloading, converting...')

        elif d['status'] == 'error':
            print('[downloader]: error')