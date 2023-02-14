import discord
from discord.ext import commands

from dotenv import load_dotenv
import os
import asyncio

from shuffle import shuffle
from shuffle.log import shuffle_logger

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# TODO: reduce intents to only those needed if possible
intents = discord.Intents.all()

# TODO: remove and parse prefix in the bot using guild config
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot.remove_command('help')

logger = shuffle_logger()
shuffle_env = os.getenv('SHUFFLE_ENV', 'dev')

async def bot_create():
    logger.info('Starting bot...')
    await bot.add_cog(shuffle.ShuffleBot(bot, logger, env=shuffle_env))
    await bot.start(TOKEN)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

try:
    loop.run_until_complete(bot_create())
except KeyboardInterrupt:
    logger.info('Keyboard interrupt received, stopping bot')
    exit(0)
# except Exception as e:
#     logger.error(f'[uncaught error] {str(e)}')
#     exit(1)
