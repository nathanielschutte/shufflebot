
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

devCommands = []
devUsers = []

# Events
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(BOT_ACTIVITY))
    print(f'{bot.user} is connected')

# Shuffle bot
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
bot.run(TOKEN)