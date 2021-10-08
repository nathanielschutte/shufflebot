
# # # # # # # # # # # #
# # # SHUFFLE BOT # # #
# # # # # # # # # # # #
#
# author: Nate
# description:
#   Playback from urls and search queries
#   Server playlists and tracks
#   Personal profile data


import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from .exceptions import ShuffleBotException, FormattedException
from .store import Storage
from .config import Config, ConfigFallback
from .aliases import Aliases, AliasesFallback

util.readConfig('config.ini', True)
FFMPEG_EXE = util.getConfig('playback', 'ffmpeg')
STORAGE_DIR = util.getConfig('storage', 'dir')

BOT_PREFIX = util.getConfig('bot', 'prefix').strip()
if not BOT_PREFIX:
    print('bot prefix error')
BOT_ACTIVITY = util.getConfig('bot', 'action')
if not BOT_ACTIVITY:
    print('bot action error')
    BOT_ACTIVITY = 'unknown'


# Shuffle bot commands
class Shuffle(commands.Cog):
    """Shuffle discord cog for ShuffleBot"""
    def __init__(self, bot, profiles=None, playlists=None, tracks=None):

        self.bot = bot

        self.usingProfiles = profiles != None
        self.usingPlaylists = playlists != None
        self.usingTracks = tracks != None
        self.profiles = profiles
        self.playlists = playlists
        self.tracks = tracks

        if self.usingProfiles:
            self.updateProfiles()

    # Server and command management
    # Make sure every player on the server has a profile
    def updateProfiles(self):
        
        store.setCollection('profiles', self.profiles)

    def argPlaylistOrTrack(arg):
        if arg != None:
            if arg == 'playlists' or arg == 'playlist' or arg == 'p':
                return 1
            elif arg == 'tracks' or arg == 'track' or arg == 't':
                return 2
        else:
            return 0
    
    # Commands
    @commands.command(help='Search online or paste a URL')
    async def play(self, ctx, arg=None):
        self.helper(arg)

    @commands.command(help='Temporarily stop playback')
    async def pause(self, ctx):
        pass

    @commands.command(help='Resume playback')
    async def resume(self, ctx):
        pass

    @commands.command(help='Permanantly stop playback')
    async def stop(self, ctx):
        pass

    @commands.command(help='Play next song in queue')
    async def skip(self, ctx):
        pass

    @commands.command(help='Show all saved playlists and tracks')
    async def list(self, ctx, arg=None):
        type = self.argPlaylistOrTrack(arg)
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

    @commands.command(help='Clear the queue')
    async def clear(self, ctx, arg, ):
        pass

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Game(BOT_ACTIVITY))
        print(f'{self.bot.user} is connected using prefix {BOT_PREFIX} and activity \'{BOT_ACTIVITY}\'')


class ShuffleBot:
    """ShuffleBot runner"""

    def __init__(self, config_file=None, aliases_file=None):
        
        if config_file is None:
            config_file = ConfigFallback.config_file
        if aliases_file is None:
            aliases_file = AliasesFallback.aliases_file

        self.config = Config(config_file)
        if self.config.use_aliases:
            self.aliases = Aliases(aliases_file)

        self.storage = None

        # Dev
        self.dev_cmds = []
        self.dev_users = []

        # Storage (needs refactor...)
        store.setDir(STORAGE_DIR)
        store.load()
        store.useCollection('profiles')
        store.useCollection('playlists')
        store.useCollection('tracks')

        # Bot creation
        self.bot = commands.Bot(command_prefix=BOT_PREFIX)
        self.cogs = [
            Shuffle(self.bot)
        ]
        self.__setup()


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
                raise ShuffleBotException('issue adding cog' + cog)