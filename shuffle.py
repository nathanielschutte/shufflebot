
# SHUFFLE BOT
#
# author: Nate
#
# Server global playlists and track store
# Personal profile data



# Commands
# - play
# - pause
# - stop
# - skip
# - queue

import discord
from discord.ext import commands

import store, util

util.readConfig('config.ini')
FFMPEG_EXE = util.getConfig('playback', 'ffmpeg')
STORAGE_DIR = util.getConfig('storage', 'dir')

BOT_PREFIX = util.getConfig('bot', 'prefix').strip()
if not BOT_PREFIX:
    print('bot prefix error')
BOT_TOKEN = util.getConfig('bot', 'token')
if not BOT_TOKEN:
    print('bot token error')

bot = commands.Bot(command_prefix=BOT_PREFIX)

devCommands = []
devUsers = []

class Shuffle(commands.Cog):
    """"""
    def __init__(self, bot):
        self.bot = bot

        self.profiles = store.getCollection('profiles')
        self.playlists = store.getCollection('playlists')
        self.tracks = store.getCollection('tracks')
    
    @commands.command(help='play track')
    async def play(self, ctx, arg):
        pass

store.setDir(STORAGE_DIR)
store.load()
store.useCollection('profiles')
store.useCollection('playlists')
store.useCollection('tracks')

bot.add_cog(Shuffle(bot))
bot.run(BOT_TOKEN)