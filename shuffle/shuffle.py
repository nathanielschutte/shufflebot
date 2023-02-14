import logging
import json
import asyncio
import os

import discord
from discord.ext import commands

from typing import Dict

from shuffle.player.player import Player

class ShuffleBot(commands.Cog):
    def __init__(self, bot: commands.Bot, logger: logging.Logger, env: str = 'dev'):
        self.bot = bot
        self.logger = logger

        self.players: Dict[int, Player] = {}

        self._env = env
        self._update_config()
        self.logger.debug(f'Loaded config: {self._env}')

    def get_player(self, guild_id: int) -> Player:
        if guild_id not in self.players:
            self.players[guild_id] = Player(guild_id, self.config)
        return self.players[guild_id]

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'-help'))
        self.logger.info('Bot is ready')

    @commands.command()
    async def ping(self, ctx):
        await ctx.send('pong')

    @commands.command()
    async def test(self, ctx):
        voice = None
        for vc in self.bot.voice_clients:
            if vc.channel.id == ctx.author.text.channel.id:
                self.logger.debug(f'bot already connected to the channel! {ctx.author.text.channel.id}')
                voice = vc.channel
        if voice is None:
            voice = await ctx.author.voice.channel.connect()
        self.logger.debug(f'Connected')
        self.logger.debug(f'Found {os.path.isfile("./files/edwk-8KJ1Js.mp3")}')
        voice.play(discord.FFmpegPCMAudio(source='./files/edwk-8KJ1Js.mp3', executable='ffmpeg'))
        self.logger.debug(f'Started playing')
        play_counter = 0
        while voice.is_playing():
            await asyncio.sleep(1)
            play_counter += 1
            if play_counter > 60:
                self.log.error(f'Track timeout out after 60 seconds')
                break
        self.logger.debug(f'Done playing')
        await voice.disconnect()

    # Play a song, or queue it if already playing a song
    # This should also 'resume' if paused
    @commands.command()
    async def play(self, ctx, *args):

        # TODO: create common argument parsers/validators/filters/converters/consumers
        query = ' '.join(args).strip()
        if query == '':
            await ctx.send('No song provided. Please try `!play <song>`')
            return

        await self.get_player(ctx.guild.id).enqueue(query, self._get_voice_channel(ctx))

    
    # Stop playback if currently playing
    @commands.command()
    async def stop(self, ctx):
        ...

    # Pause playback if currently playing
    @commands.command()
    async def pause(self, ctx):
        ...

    # Resume playback if currently paused
    @commands.command()
    async def resume(self, ctx):
        ...

    # SKip the current song
    # Optional: provide an index or song name to skip to
    @commands.command()
    async def skip(self, ctx):
        ...

    # View the queue
    @commands.command()
    async def list(self, ctx):
        ...

    # Empty the queue
    @commands.command()
    async def clear(self, ctx):
        ...

    # ADMIN COMMANDS
    # Reload configuration for this guild
    @commands.command()
    async def reload(self, ctx):
        ...

    # Clean files for this guild
    @commands.command()
    async def clean(self, ctx):
        ...

    def _get_voice_channel(self, ctx):
        target = ctx.author
        if target.voice != None and target.voice.channel != None:
            self.logger.debug(f'Got target ({target.display_name}) channel: {target.voice.channel.name}')
            return target.voice.channel
        else: # no voice channel, do nothing
            self.logger.info(f'No voice channel for target {target.display_name}')
            return None
        

    # Update guild based on guild configuration in database
    def _update_config(self):
        with open(f'config/{self._env}.json', 'r') as f:
            self.config = json.load(f)
