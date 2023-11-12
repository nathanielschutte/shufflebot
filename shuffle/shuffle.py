import logging
import json
import asyncio
import os

import discord
from discord.ext import commands

from typing import Dict

from shuffle.player.player import Player
from shuffle.constants import GOD_IDS


class ShuffleRebootException(Exception):
    ...

class ShuffleBot(commands.Cog):
    def __init__(self, bot: commands.Bot, logger: logging.Logger, env: str = 'dev'):
        self.bot = bot
        self.logger = logger

        self.players: Dict[int, Player] = {}

        self._env = env
        self._update_config()
        self.logger.debug(f'Loaded config: {self._env}, prefix: {self.config["prefix"]}')

        commands_file = f'shuffle/shuffle.json'
        if not os.path.isfile(commands_file):
            raise Exception(f'Commands file not found: {commands_file}')
        self.commands_file = commands_file

        try:
            with open(commands_file, 'r') as file:
                self.commands = json.loads(file.read())
        except Exception as e:
            raise Exception(f'Commands file not parseable: {commands_file} [{str(e)}]')

        self.helper = ShuffleHelp(commands=self.commands)

        self.logger.debug('Done creating ShuffleBot')


    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{self.config["prefix"]}help'))
        self.logger.info('Bot is ready')


    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        content = msg.content.strip()

        if not content[0] == self.config['prefix']:
            return

        command_parts = content[1:].split()
        command = command_parts[0]
        args = command_parts[1:]

        # check for aliases
        for cmd, data in self.commands.items():
            if 'aliases' in data and command in data['aliases']:
                command = cmd
                break

        # check for declared command
        if command in self.commands:

            # command disabled
            if 'disabled' in self.commands[command] and self.commands[command]['disabled'] == 1:
                return

            # admin
            if 'permission' in self.commands[command] \
                and len(self.commands[command]['permission']) > 0 \
                and self.commands[command]['permission'].lower() != 'any':
                perm_tag = self.commands[command]['permission'].lower()

                # need to set up admin permissions....right now just me
                if perm_tag == 'admin' and str(msg.author.id) not in GOD_IDS:
                    await msg.channel.send(f'You are not authorized to run command `{command}`')
                    return

            # self.logger.debug(f'user {msg.author.display_name} called on: \'{command}\'')

            method_name = command

            if 'function' in self.commands[command]:
                method_name = self.commands[command]['function']

            if hasattr(self, method_name):
                method = getattr(self, method_name)
                if asyncio.iscoroutinefunction(method):

                    # check arg minimum requirement
                    if 'argmin' in self.commands[command] and len(args) < self.commands[command]['argmin']:
                        if 'usage' in self.commands[command]:
                            await msg.channel.send(f'Usage: `{self.config["prefix"]}{command} {self.commands[command]["usage"]}`')
                        return
                    
                    self.logger.debug(f'Executing: \'{command}({" ".join(args)})\'')

                    if msg.guild is None:
                        self.logger.error(f'No guild ID found in message context!')

                    assert msg.guild is not None
                    player = self._get_player(msg.guild.id)
                    asyncio.get_event_loop().create_task(method(msg, player, *args))
                else:
                    self.logger.error(f'function not coroutine for command: {command}')
            else:
                self.logger.error(f'could not find function to call for command: {command}')



        #self.logger.debug(f'got message: {msg.content.strip()}')


    # Test command
    async def ping(self, ctx: discord.Message, _):
        self.logger.debug('ping received')
        await ctx.channel.send('pong')

    async def restart(self, ctx: discord.Message, _):
        await ctx.channel.send('Rebooting the bot...')
        raise ShuffleRebootException

    # Play a song, or queue it if already playing a song
    # This should also 'resume' if paused
    async def play(self, ctx: discord.Message, player: Player, *args):
        # TODO: create common argument parsers/validators/filters/converters/consumers
        query = ' '.join(args).strip()
        query = query[:min(len(query), 100)]
        if query == '':
            await ctx.channel.send('No song provided. Please try `!play <song>`')
            return

        self.logger.debug(f'Searching for query: {query}')   

        message = await ctx.channel.send(f'Searching for `{query}` ...')
        track = await player.enqueue(query, self._get_voice_channel(ctx))
        position = player.queue.length

        if position > 0:
            await message.edit(content=f'Queued `{track.title}` at position {position}')
        else:
            await message.edit(content=f'Playing `{track.title}`')
    

    # Stop playback if currently playing
    async def stop(self, ctx, player, *args):
        await player.stop()

    # Pause playback if currently playing
    async def pause(self, ctx, player, *args):
        ...

    # Resume playback if currently paused
    async def resume(self, ctx, player, *args):
        ...

    # SKip the current song
    # Optional: provide an index or song name to skip to
    async def skip(self, ctx, player, *args):
        result = await player.skip()
        if result == -1:
            await ctx.channel.send('The queue is empty!')
        elif isinstance(result, int):
            await ctx.channel.send(f'Skipping current song, {result+1} songs left in the queue')

    # View the queue
    async def list(self, ctx, player: Player, *args):
        current_track = '_none_'
        if player.queue.is_playing:

            assert player.queue.current is not None
            current_track = f'*{player.queue.current.title}*'

        desc = [f'{i+1}: {t.title}' for i, t in enumerate(player.list())]
        if len(desc) == 0:
            desc = ['_none_']
            
        desc_str = '\n'.join(desc)

        embed = discord.Embed()
        embed.add_field(name='Current', value=current_track, inline=False)
        embed.add_field(name='Queue', value=desc_str, inline=False)
        await ctx.channel.send(embed=embed)

    # ADMIN COMMANDS
    # Empty the queue
    async def clear(self, ctx):
        ...


    
    async def help(self, msg: discord.Message, player, *args):
        await self.helper.send_bot_help(msg.channel, self.config['prefix'])



    # Get command author's voice channel, if it exists
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

    def _get_player(self, guild_id: int) -> Player:
        if guild_id not in self.players:
            self.logger.debug(f'Creating player for guild {guild_id}')
            self.players[guild_id] = Player(guild_id, self.config, self.bot)
        return self.players[guild_id]


class ShuffleHelp(commands.HelpCommand):
    '''Bot commands help'''

    def __init__(self, commands):
        super().__init__()

        self.commands = commands
        

    async def send_bot_help(self, channel, prefix):
        embed = discord.Embed(title=f'Shuffle help:')
        for cmd_name, cmd in self.commands.items():

            # skip commands that have a permission besides 'any', or are disabled
            if 'permission' in cmd and cmd['permission'].lower() != 'any':
                continue

            if 'disabled' in cmd and cmd['disabled'] == 1:
                continue

            if 'desc' not in cmd:
                cmd['desc'] = ''
            if 'usage' not in cmd:
                cmd['usage'] = ''

            cmdstr = f'{cmd["desc"]}\n`{prefix}{cmd_name} {cmd["usage"]}`'
            embed.add_field(name=f'{cmd_name}:', value=cmdstr, inline=False)
            
        await channel.send(embed=embed)


    async def send_cog_help(self, cog):
        return await super().send_cog_help(cog)


    async def send_group_help(self, group):
        return await super().send_group_help(group)


    async def send_command_help(self, command):
        return await super().send_command_help(command)

