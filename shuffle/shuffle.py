import logging
import json
import asyncio
import os
import traceback

import discord
from discord.ext import commands

from typing import Dict, Optional

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
        try:
            content = msg.content.strip()

            if not content or content[0] != self.config['prefix']:
                return

            command_parts = content[1:].split()
            if not command_parts:
                return
                
            command = command_parts[0]
            args = command_parts[1:]

            self.logger.debug(f"Command received: {command} with args: {args} from user: {msg.author.name}")

            for cmd, data in self.commands.items():
                if 'aliases' in data and command in data['aliases']:
                    command = cmd
                    break

            # check for declared command
            if command in self.commands:
                # command disabled
                if 'disabled' in self.commands[command] and self.commands[command]['disabled'] == 1:
                    self.logger.debug(f"Command {command} is disabled")
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

                        # Handle DMs properly
                        if msg.guild is None:
                            self.logger.info(f'Command received in DM from {msg.author.name}, ignoring')
                            await msg.channel.send("Sorry, commands only work in servers, not in DMs.")
                            return

                        try:
                            player = self._get_player(msg.guild.id)
                            # Execute command directly with proper error handling
                            await method(msg, player, *args)
                        except Exception as e:
                            error_msg = f'Error executing command {command}: {str(e)}'
                            self.logger.error(error_msg)
                            self.logger.error(traceback.format_exc())
                            # await msg.channel.send(f"Error: {str(e)}")
                    else:
                        self.logger.error(f'function not coroutine for command: {command}')
                else:
                    self.logger.error(f'could not find function to call for command: {command}')
            else:
                # Command not found, let user know
                self.logger.debug(f"Unknown command: {command}")
                await msg.channel.send(f"Unknown command: `{command}`. Try `{self.config['prefix']}help` for a list of commands.")
        except Exception as e:
            # Catch-all for any other errors in command processing
            self.logger.error(f"Unexpected error processing message: {str(e)}")
            self.logger.error(traceback.format_exc())


    # Test command
    async def ping(self, ctx: discord.Message, _):
        self.logger.debug('ping received')
        await ctx.channel.send('pong')

    async def restart(self, ctx: discord.Message, _):
        await ctx.channel.send('Rebooting the bot...')
        raise ShuffleRebootException

    # Update the play, stop, and resume methods in shuffle.py

    # Play command that handles both new songs and resuming
    async def play(self, ctx: discord.Message, player: Player, *args):
        query = ' '.join(args).strip()
        
        # If no query provided, try to resume playback
        if query == '':
            voice_channel = self._get_voice_channel(ctx)
            if voice_channel is None:
                await ctx.channel.send("You need to join a voice channel first!")
                return
                
            self.logger.debug(f'No query provided, attempting to resume playback')
            
            success = await player.resume(voice_channel)
            if success:
                await ctx.channel.send("Resuming playback!")
            else:
                await ctx.channel.send("Nothing to resume. Use `-play <song>` to play a song.")
            return

        # Limit query length
        query = query[:min(len(query), 100)]

        voice_channel = self._get_voice_channel(ctx)
        if voice_channel is None:
            await ctx.channel.send("You need to join a voice channel first!")
            return

        self.logger.debug(f'Searching for query: {query}')   

        message = await ctx.channel.send(f'Searching for `{query}` ...')
        try:
            track = await player.enqueue(query, voice_channel)
            position = player.queue.length

            if position > 0:
                await message.edit(content=f'Queued `{track.title}` at position {position}')
            else:
                await message.edit(content=f'Playing `{track.title}`')
        except Exception as e:
            self.logger.error(f"Error playing {query}: {str(e)}")
            self.logger.error(traceback.format_exc())
            await message.edit(content=f"Error playing `{query}`, contact admin")


    async def stop(self, ctx, player, *args):
        try:
            await player.stop()
            await ctx.channel.send("Playback paused. Use `-play` or `-resume` to continue.")
        except Exception as e:
            self.logger.error(f"Error pausing playback: {str(e)}")
            self.logger.error(traceback.format_exc())
            await ctx.channel.send(f"Error pausing playback, contact admin")


    async def resume(self, ctx, player, *args):
        try:
            voice_channel = self._get_voice_channel(ctx)
            if voice_channel is None:
                await ctx.channel.send("You need to join a voice channel first!")
                return
                
            success = await player.resume(voice_channel)
            if success:
                await ctx.channel.send("Resuming playback!")
            else:
                await ctx.channel.send("Nothing to resume. Use `-play <song>` to play a song.")
        except Exception as e:
            self.log.error(f"Error resuming playback: {str(e)}")
            await ctx.channel.send(f"Error resuming playback: {str(e)}")

    # SKip the current song
    # Optional: provide an index or song name to skip to
    async def skip(self, ctx, player, *args):
        try:
            result = await player.skip()
            if result == -1:
                await ctx.channel.send('The queue is empty!')
            elif isinstance(result, int):
                await ctx.channel.send(f'Skipping current song, {result} songs left in the queue')
        except Exception as e:
            self.logger.error(f"Error skipping track: {str(e)}")
            await ctx.channel.send(f"Error skipping track: {str(e)}")

    # View the queue
    async def list(self, ctx, player: Player, *args):
        try:
            current_track = '_none_'
            if player.queue.is_playing:
                if player.queue.current is not None:
                    current_track = f'*{player.queue.current.title}*'
                else:
                    current_track = '*Unknown track*'

            desc = [f'{i+1}: {t.title}' for i, t in enumerate(player.list())]
            if len(desc) == 0:
                desc = ['_none_']
                
            desc_str = '\n'.join(desc)

            embed = discord.Embed()
            embed.add_field(name='Current', value=current_track, inline=False)
            embed.add_field(name='Queue', value=desc_str, inline=False)
            await ctx.channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error listing queue: {str(e)}")
            await ctx.channel.send(f"Error listing queue: {str(e)}")

    # ADMIN COMMANDS
    # Empty the queue
    async def clear(self, ctx, player, *args):
        try:
            await player.clear()
            await ctx.channel.send("Queue cleared.")
        except Exception as e:
            self.logger.error(f"Error clearing queue: {str(e)}")
            await ctx.channel.send(f"Error clearing queue: {str(e)}")
    
    async def help(self, msg: discord.Message, player, *args):
        await self.helper.send_bot_help(msg.channel, self.config['prefix'])

    # Get command author's voice channel, if it exists
    def _get_voice_channel(self, ctx) -> Optional[discord.VoiceChannel]:
        target = ctx.author
        if target.voice != None and target.voice.channel != None:
            self.logger.debug(f'Got target ({target.display_name}) channel: {target.voice.channel.name}')
            return target.voice.channel
        else: # no voice channel, do nothing
            self.logger.info(f'No voice channel for target {target.display_name}')
            return None
        
    # Update guild based on guild configuration in database
    def _update_config(self):
        config_path = f'config/{self._env}.json'
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config from {config_path}: {str(e)}")
            # Provide default config to prevent crash
            self.config = {"prefix": "!", "download_path": "/var/lib/shuffle/audio"}

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

