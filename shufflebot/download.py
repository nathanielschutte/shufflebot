
# Download videos

from __future__ import unicode_literals
import youtube_dl
import validators

# test: https://www.youtube.com/watch?v=oR4uKcvQbGQ

class Downloader:
    """YouTube mp3 downloader"""

    def __init__(self, savedir=None) -> None:

        if savedir is not None and savedir[-1] != '/':
            savedir += '/'

        self.savedir = savedir
        self.download_status = None

        self.opts = {
            'outtmpl': '%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [self.__status_hook],
        }

        self.ydl = youtube_dl.YoutubeDL(self.opts)

    # Find out what video title is associated with the given URL or query string
    async def get_title(self, string):
        
        # determine if URL or query
        isUrl = self.__check_url_vs_query(string)
        print(f'{isUrl=}')

        # extract info no download
        with self.ydl:
            if isUrl:
                result = self.ydl.extract_info(string, download=False)
                print(f'URL RESULT: {result}')

    # Is the string a URL
    def __check_url_vs_query(self, string):
        
        # multiple words passed but maybe the first one is still a URL
        if string.find(' ') != -1:
            return self.__check_url_vs_query(string[:string.find(' ')])
        
        # just one word, see if it's a URL
        else:
            return validators.url(string)

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