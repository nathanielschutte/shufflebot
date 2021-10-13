
# # # # # # # # # # # #
# # # SHUFFLE BOT # # #
# # # # # # # # # # # #

# author: Nate
# description:
#   Playback from urls and search queries
#   Server-stored playlists and tracks


import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from youtube_dl import downloader

from .exceptions import ShuffleBotException, FormattedException
from .store import Storage
from .config import Config, ConfigFallback
from .aliases import Aliases, AliasesFallback
from .download import Downloader
from .player import Player

class ShuffleBot:
    """ShuffleBot runner"""

    def __init__(self, config_file=None, aliases_file=None):
        
        # Config and command aliases
        if config_file is None:
            config_file = ConfigFallback.config_file
        if aliases_file is None:
            aliases_file = AliasesFallback.aliases_file

        config = Config(config_file)
        if config.use_aliases:
            self.aliases = Aliases(aliases_file)

        # Server storage object
        self.storage = Storage()
        
        # Audio player objects indexed by channel ID
        self.players = {}

        # Dev commands
        self.dev_cmds = []
        self.dev_users = []

        # Storage
        self.storage.load()
        self.storage.useCollection('profiles')
        self.storage.useCollection('playlists')
        self.storage.useCollection('tracks')

        # Bot creation
        self.bot = commands.Bot(command_prefix=config.bot_prefix)
        self.cogs = [

            # Shuffle cog needs bot ref and controller ref
            Shuffle(self.bot, self, config)
        ]
        self.__setup()


    # Return 0 to exit, 1 to restart
    def run(self):
        load_dotenv()
        token = os.getenv('DISCORD_TOKEN')
        if token is None:
            raise ShuffleBotException('token not found in environment variables')

        self.bot.run(token)

    def __setup(self):
        for cog in self.cogs:
            try:
                self.bot.add_cog(cog)
            except:
                raise ShuffleBotException('issue adding cog ' + type(cog).__name__)

# Shuffle bot commands
class Shuffle(commands.Cog):
    """Shuffle discord cog for ShuffleBot"""

    def __init__(self, bot: commands.Bot, control: ShuffleBot, config: Config):

        self.bot = bot
        self.control = control
        self.config = config

        self.profiles = control.storage.getCollection('profiles')
        self.playlists = control.storage.getCollection('playlists')
        self.tracks = control.storage.getCollection('tracks')

    def __argPlaylistOrTrack(arg):
        if arg != None:
            if arg == 'playlists' or arg == 'playlist' or arg == 'p':
                return 1
            elif arg == 'tracks' or arg == 'track' or arg == 't':
                return 2
        else:
            return 0
    
    # Commands
    # play
    @commands.command(help='Search online or paste a URL')
    async def play(self, ctx, *args):
        
        # track title or URL
        arg = ''.join(args).strip()
        print(f'play: query is \'{arg}\'')

        user = ctx.message.author
        channel_id = user.voice.voice_channel.id

        # new player for this audio channel
        if channel_id not in self.control.players:
            # send initial message
            self.control.players[channel_id] = Player()
        else:
            # update Player messages
            pass
        
        # Check if in audiocache
            # Is -> ref mp3
            # Isnt -> use downloader
                # Check audio cache size, remove last vid until under maximum
                # Ref new mp3
        # Start bplay
        
        pass

    # pause
    @commands.command(help='Temporarily stop playback')
    async def pause(self, ctx):
        pass

    # resume
    @commands.command(help='Resume playback')
    async def resume(self, ctx):
        pass

    # stop
    @commands.command(help='Permanantly stop playback')
    async def stop(self, ctx):
        pass

    # skip
    @commands.command(help='Play next song in queue')
    async def skip(self, ctx):
        pass

    # list
    @commands.command(help='Show all saved playlists and tracks')
    async def list(self, ctx, arg=None):
        type = self.__argPlaylistOrTrack(arg)
        title = ''
        if type == 0:
            title = 'Playlist and Tracks'

        embed = discord.Embed(title=title)

        # get playlists
        if type == 0 or type == 1:
            content = ''
            if len(self.playlists) > 0:
                pass
            else:
                content = 'none'
            embed.add_field(name='Playlists', value=content, inline=False)
                
        # get tracks
        if type == 0 or type == 2:
            content = ''
            if len(self.tracks) > 0:
                pass
            else:
                content = 'none'
            embed.add_field(name='Tracks', value=content, inline=False)

        await ctx.send(embed=embed)

    # clear
    @commands.command(help='Clear the queue')
    async def clear(self, ctx, arg, ):
        pass

    # Events
    # on ready
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Game(self.config.bot_isplaying))
        print(f'{self.bot.user} is connected using prefix {self.config.bot_prefix}')
