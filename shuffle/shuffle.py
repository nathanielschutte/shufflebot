import logging
import os
import asyncio

import discord
from discord.ext import commands

from shuffle.player.download import Downloader
from shuffle.constants import PROJECT_ROOT

class ShuffleBot(commands.Cog):

    def __init__(self, bot: commands.Bot, logger: logging.Logger):
        self.bot = bot
        self.logger = logger
        self._d = Downloader()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'`!help`'))
        self.logger.info('Bot is ready')

    @commands.command()
    async def ping(self, ctx):
        await ctx.send('pong')

    @commands.command()
    async def connect(self, ctx):
        if ctx.author.voice and ctx.author.voice.channel:
            self.logger.info(f'Connecting to voice channel [{ctx.author.voice.channel.name}]')
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("You are not connected to a voice channel")

    @commands.command()
    async def download(self, ctx: discord.ext.commands.Context, *args):
        test_hash = 'Htaj3o3JD8I'
        self._d.download(test_hash)
        await ctx.send(f'Downloading YouTube [{test_hash}]')

    @commands.command()
    async def play(self, ctx: commands.Context, *args):

        query = ' '.join(args).strip()
        if query == '':
            await ctx.send('No song provided. Please try `!play <song>`')
            return

        url = await asyncio.get_event_loop().run_in_executor(None, lambda: self._d.get_url(' '.join(args)))
        await ctx.send(f'Playing YouTube [{url}]')
        self.logger.info(f'Playing YouTube [{url}]')

        # get voice channel
        target = ctx.author
        voice_channel = None
        if target.voice != None and target.voice.channel != None:
            voice_channel = target.voice.channel
            self.logger.debug(f'target: {target.display_name}')
            self.logger.debug(f'channel name: {voice_channel.name}')
        else: # no voice channel, do nothing
            self.logger.info(f'No voice channel for target {target.display_name}')
            return

        # join voice channel
        voice = await voice_channel.connect()
        self.logger.debug('Joined voice channel')
        voice.play(
            discord.FFmpegPCMAudio(
                url,
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                options='-vn'
            ),
            after=lambda e: self.logger.info('Done playing', e)
        )
        self.logger.debug('Playing in voice channel')
        while voice.is_playing():
            await asyncio.sleep(1)
        self.logger.debug('Done playing')
        await voice.disconnect()
        self.logger.debug('Disconnected from voice channel')
