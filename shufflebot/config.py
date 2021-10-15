
import os
import shutil
from shufflebot.exceptions import FormattedException

from .util import ConfigReader

# Config read (using util) to constants
class Config:
    """Holds a config state"""

    def __init__(self, file):
        self.file = file

        if not os.path.isfile(self.file):

            # Missing extension
            if os.path.isfile(self.file + '.ini'):
                self.file += '.ini'

            # Use config template file
            elif os.path.isfile('config/config_template.ini'):
                shutil.copy('config/config_template.ini', self.file)
            
            # All config files missing
            else:
                raise FormattedException('Config files not found')

        config = ConfigReader(verbose=False)
        config.read(file)

        # Check all sections exist...

        # Add all the config vars
        # [aliases]
        self.use_aliases = config.get_bool('aliases', 'use_aliases', ConfigFallback.use_aliases)
        self.aliases_file = config.get('aliases', 'aliases_file', ConfigFallback.aliases_file)

        # [bot]
        self.bot_prefix = config.get('bot', 'prefix', ConfigFallback.bot_prefix)
        self.bot_isplaying = config.get('bot', 'isplaying', ConfigFallback.bot_isplaying)
        self.bot_icon = config.get('bot', 'icon', ConfigFallback.bot_icon)

        # [cache]
        self.cache_cap = config.get('cache', 'capacity', ConfigFallback.cache_cap)

        # [storage]
        self.persistdir = config.get('storage', 'persistdir', ConfigFallback.persistdir)
        self.audiodir = config.get('storage', 'audiodir', ConfigFallback.audiodir)
        if self.audiodir[-1] != '/':
            self.audiodir += '/'

        # [ffmpeg]
        self.ffmpegdir = config.get('ffmpeg', 'exedir', ConfigFallback.exedir)
        self.ffmpegexe = config.get('ffmpeg', 'ffmpeg', ConfigFallback.ffmpeg)
        self.codec = config.get('ffmpeg', 'codec', ConfigFallback.codec)

    # check config values
    def config_checks():
        pass

    # check if config is missing any values in config_template.ini
    def config_diff():
        template_path = 'config/config_template.ini'

# Config defaults for fallback values
class ConfigFallback:
    config_file = 'config/config.ini'
    use_aliases = True
    aliases_file = 'config/aliases.json'

    bot_prefix = '!'
    bot_isplaying = 'Fortnite'
    bot_icon = ''

    cache_cap = 10

    persistdir = 'storage'
    audiodir = 'audiocache'

    exedir = 'bin'
    ffmpeg = 'ffmpeg.exe'
    codec = 'mp3'