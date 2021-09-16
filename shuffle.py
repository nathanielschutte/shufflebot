
# # # # # # # # # # # #
# # # SHUFFLE BOT # # #
# # # # # # # # # # # #
#
# author: Nate
# description:
#   Playback from urls and search queries
#   Server playlists and tracks
#   Personal profile data


# Commands
# - play
# - pause
# - stop
# - skip
# - queue

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

import store, util

# Config
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

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

bot = commands.Bot(command_prefix=BOT_PREFIX)

# Dev
devCommands = []
devUsers = []

# Events
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(BOT_ACTIVITY))
    print(f'{bot.user} is connected using prefix {BOT_PREFIX} and activity \'{BOT_ACTIVITY}\'')

# Shuffle bot commands
class Shuffle(commands.Cog):
    """"""
    def __init__(self, bot):
        self.bot = bot

        self.profiles = store.getCollection('profiles')
        self.playlists = store.getCollection('playlists')
        self.tracks = store.getCollection('tracks')

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
    @commands.command(help='Search youtube or paste a URL')
    async def play(self, ctx, arg=None):
        self.helper(arg)

    @commands.command(help='Play a playlist')
    async def playlist(self, ctx, arg):
        pass

    @commands.command(help='Play a track')
    async def track(self, ctx, arg):
        pass

    @commands.command(help='Temporarily stop playback')
    async def pause(self, ctx):
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

    @commands.command(help='Create a new playlist or track')
    async def create(self, ctx, arg, ):
        type = self.argPlaylistOrTrack()

# Storage
store.setDir(STORAGE_DIR)
store.load()
store.useCollection('profiles')
store.useCollection('playlists')
store.useCollection('tracks')

# Bot
bot.add_cog(Shuffle(bot))
bot.run(TOKEN)