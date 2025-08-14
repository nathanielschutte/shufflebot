import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('discord.voice_state').setLevel(logging.DEBUG)
logging.getLogger('discord.gateway').setLevel(logging.DEBUG)

def patch_discord_voice():
    """Apply the fix from PR #10210 without modifying discord.py files"""
    import sys
    
    # This must be done before importing discord
    if 'discord' in sys.modules:
        print("WARNING: Discord already imported, patch may not work fully")
    
    # Import what we need
    import discord.gateway
    
    # Store original
    original_voice_state_update = discord.gateway.DiscordVoiceWebSocket.send_as_json
    
    # Create patched version
    async def patched_send_as_json(self, data):
        # Log what we're sending
        import json
        print(f"[VOICE WS] Sending: {json.dumps(data, indent=2)}")
        
        # Call original
        return await original_voice_state_update(self, data)
    
    # Apply patch
    discord.gateway.DiscordVoiceWebSocket.send_as_json = patched_send_as_json
    
    print("✓ Applied discord.py voice connection patch")

# Apply the patch before importing anything else
patch_discord_voice()


# Once discord.py fixes this issue, we can remove this patch (ALL ABOVE THIS LINE)

import discord
from discord.ext import commands

from dotenv import load_dotenv
import os
import asyncio
import time

from shuffle import shuffle
from shuffle.log import shuffle_logger

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# TODO: reduce intents to only those needed if possible
intents = discord.Intents.all()
intents.voice_states = True

# TODO: remove and parse prefix in the bot using guild config
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot.remove_command('help')

logger = shuffle_logger()
shuffle_env = os.getenv('SHUFFLE_ENV', 'dev')

async def bot_create():
    logger.info('Starting bot...')
    shuffle_cog = shuffle.ShuffleBot(bot, logger, env=shuffle_env)
    await bot.add_cog(shuffle_cog)
    
    @bot.event
    async def on_ready():
        logger.info('Bot connected, waiting for Discord to stabilize...')
        await asyncio.sleep(2)  # Give Discord time to fully initialize
        logger.info('Bot is fully ready')
    
    await bot.start(TOKEN)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

while True:
    try:
        loop.run_until_complete(bot_create())
    except KeyboardInterrupt:
        logger.info('Keyboard interrupt received, stopping bot')
        exit(0)
    except shuffle.ShuffleRebootException:
        logger.info('Received a reboot signal. Rebooting the bot...')
        time.sleep(2)
    except Exception as e:
        logger.error(f'[uncaught error] {str(e)}')
        exit(1)
