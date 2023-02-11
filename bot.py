import discord
from discord.ext import commands

from dotenv import load_dotenv
import os
import logging
import asyncio

from src.shuffle import shuffle

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

logger = logging.getLogger('shufflebot')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] |   %(message)s')
file_handle = logging.FileHandler('out.log', encoding='utf-8')
file_handle.setFormatter(formatter)
logger.addHandler(file_handle)
console_handle = logging.StreamHandler()
console_handle.setFormatter(formatter)
logger.addHandler(console_handle)

async def bot_create():
    logger.info('Starting bot...')
    await bot.add_cog(shuffle.ShuffleBot(bot))
    await bot.start(TOKEN)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

loop.run_until_complete(bot_create())
