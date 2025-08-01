import os
import logging
from typing import List, Callable
from dataclasses import dataclass
import random
import string
import time

import yt_dlp as youtube_dl

from shuffle.log import shuffle_logger
from shuffle.player.models.Track import Track
from shuffle.player.stream import Stream
from shuffle.constants import PROJECT_ROOT

class YoutubeStream(Stream):
    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)

        self.logger = shuffle_logger('youtube')
        self.savedir = 'db/audio'
        
        # Base options that work well to avoid 403 errors
        self._base_opts = {
            # Don't specify format - let yt-dlp choose the best automatically

            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'ignoreerrors': False,
            'no_playlist': True,
            # Use different extractor approaches
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            }
        }

    def download(self, video_hash: str, path: str) -> None:
        actual_url = f'https://www.youtube.com/watch?v={video_hash}'
        self.logger.info(f'Downloading {actual_url}')
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        
        opts = self._base_opts.copy()
        opts.update({
            'outtmpl': path,
            'skip_download': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })
        
        with youtube_dl.YoutubeDL(opts) as ydl:
            ydl.download([actual_url])

    def get_track(self, query: str) -> Track:
        """Get track info with better error handling"""
        
        # Create options for this specific request
        opts = self._base_opts.copy()
        
        # Rotate user agents
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        ]
        
        opts['user_agent'] = random.choice(user_agents)
        
        # Check for cookies file
        cookie_file = os.path.join(PROJECT_ROOT, 'config', 'cookies.txt')
        if os.path.exists(cookie_file):
            opts['cookiefile'] = cookie_file
            self.logger.debug("Using cookies file")
        
        try:
            with youtube_dl.YoutubeDL(opts) as ydl:
                # Search for the video
                self.logger.debug(f"Searching for: {query}")
                result = ydl.extract_info(f"ytsearch:{query}", download=False)
                
                if not result or 'entries' not in result or not result['entries']:
                    self.logger.error(f"No results found for query: {query}")
                    return None
                
                # Get first result
                entry = result['entries'][0]
                
                # Extract info for the specific video to get formats
                video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                self.logger.debug(f"Extracting info for: {video_url}")
                
                # Let yt-dlp handle format selection automatically
                video_info = ydl.extract_info(video_url, download=False)
                
                # Get the best audio URL
                audio_url = self._extract_audio_url(video_info)
                
                if not audio_url:
                    self.logger.error(f"Failed to extract audio URL")
                    return None
                
                return Track(
                    id=video_info.get('id', 'unknown'),
                    title=video_info.get('title', 'Unknown Title'),
                    query=query,
                    web_url=video_url,
                    audio_url=audio_url,
                    duration=video_info.get('duration', -1)
                )
                
        except youtube_dl.utils.DownloadError as e:
            error_msg = str(e)
            if 'Sign in to confirm' in error_msg:
                self.logger.error("YouTube requires sign-in. Consider using cookies.")
            elif '403' in error_msg:
                self.logger.error("Got 403 error. YouTube is blocking requests.")
            else:
                self.logger.error(f"Download error: {error_msg}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    def _extract_audio_url(self, info_dict: dict) -> str:
        """Extract the best audio URL from video info"""
        
        # Check if yt-dlp already selected a URL for us
        if 'url' in info_dict and info_dict['url']:
            self.logger.debug("Using URL selected by yt-dlp")
            return info_dict['url']
        
        # Otherwise look through formats
        formats = info_dict.get('formats', [])
        
        if not formats:
            # Check if there's a direct URL in requested_formats
            requested_formats = info_dict.get('requested_formats', [])
            if requested_formats and requested_formats[0].get('url'):
                self.logger.debug("Using URL from requested_formats")
                return requested_formats[0]['url']
            
            self.logger.warning("No formats found in video info")
            return None
        
        # Log available formats for debugging
        self.logger.debug(f"Total formats available: {len(formats)}")
        
        # Try to find audio-only formats first
        audio_only_formats = []
        audio_with_video_formats = []
        
        for f in formats:
            if f.get('url'):  # Must have a URL
                # Audio only format (no video codec)
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_only_formats.append(f)
                # Format with audio (might have video too)
                elif f.get('acodec') != 'none':
                    audio_with_video_formats.append(f)
        
        # Prefer audio-only formats
        if audio_only_formats:
            self.logger.info(f"Found {len(audio_only_formats)} audio-only formats")
            # Sort by audio bitrate (handle None values)
            audio_only_formats.sort(
                key=lambda f: float(f.get('abr', 0) or 0), 
                reverse=True
            )
            best_format = audio_only_formats[0]
        elif audio_with_video_formats:
            self.logger.info(f"No audio-only formats, using format with video ({len(audio_with_video_formats)} available)")
            # For video+audio formats, prefer lower video quality to save bandwidth
            # Sort by audio bitrate
            audio_with_video_formats.sort(
                key=lambda f: float(f.get('abr', 0) or 0), 
                reverse=True
            )
            best_format = audio_with_video_formats[0]
        else:
            # Last resort - just use the first format with a URL
            formats_with_url = [f for f in formats if f.get('url')]
            if formats_with_url:
                self.logger.warning("No audio formats found, using first available format")
                best_format = formats_with_url[0]
            else:
                self.logger.error("No formats with URLs found")
                return None
        
        self.logger.info(
            f"Selected format {best_format.get('format_id', 'unknown')} - "
            f"{best_format.get('ext', 'unknown')} - "
            f"video={best_format.get('vcodec', 'unknown')} "
            f"audio={best_format.get('acodec', 'unknown')} @ {best_format.get('abr', 'unknown')}kbps"
        )
        
        return best_format.get('url')

    def is_ready(self) -> bool:
        return True