
# # # # # # # # # # # #
# # # SHUFFLE BOT # # #
# # # # # # # # # # # #

# author: Nate
# description:
#   Playback from urls and search queries
#   Server-stored playlists and tracks


import os
from time import sleep
import discord
from discord import embeds
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
from threading import Thread

from .cache import Cache

from .exceptions import DownloadException, ShuffleBotException, FormattedException
from .store import Storage
from .config import Config, ConfigFallback
from .aliases import Aliases, AliasesFallback
from .download import Downloader
from .player import Player, PlayerState

class ShuffleBot:
    """ShuffleBot runner"""

    def __init__(self, config_file=None, aliases_file=None):
        
        # Config and command aliases
        if config_file is None:
            config_file = ConfigFallback.config_file
        if aliases_file is None:
            aliases_file = AliasesFallback.aliases_file

        config = Config(config_file)
        if config.use_aliases:
            self.aliases = Aliases(aliases_file)

        # Server storage object
        self.storage = Storage()

        # Audio file cache
        self.cache = Cache(config.audiodir, config.cache_cap)
        
        # Audio player objects indexed by channel ID
        self.players = {}

        # Dev commands
        self.dev_cmds = []
        self.dev_users = []

        # Storage
        self.storage.load()
        self.storage.useCollection('profiles')
        self.storage.useCollection('playlists')
        self.storage.useCollection('tracks')

        # Bot creation
        self.bot = commands.Bot(command_prefix=config.bot_prefix)
        self.cogs = [

            # Shuffle cog needs bot ref and controller ref
            Shuffle(self.bot, self, config)
        ]
        self.__setup()


    # Return 0 to exit, 1 to restart
    def run(self):
        load_dotenv()
        token = os.getenv('DISCORD_TOKEN')
        if token is None:
            raise ShuffleBotException('token not found in environment variables')

        self.bot.run(token)

    def __setup(self):
        for cog in self.cogs:
            try:
                self.bot.add_cog(cog)
            except:
                raise ShuffleBotException('issue adding cog ' + type(cog).__name__)

# Shuffle bot commands
class Shuffle(commands.Cog):
    """Shuffle discord cog for ShuffleBot"""

    def __init__(self, bot: commands.Bot, control: ShuffleBot, config: Config):

        self.bot = bot
        self.control = control
        self.config = config

        self.profiles = control.storage.getCollection('profiles')
        self.playlists = control.storage.getCollection('playlists')
        self.tracks = control.storage.getCollection('tracks')

    def __arg_playlist_or_track(arg):
        if arg != None:
            if arg == 'playlists' or arg == 'playlist' or arg == 'p':
                return 1
            elif arg == 'tracks' or arg == 'track' or arg == 't':
                return 2
        else:
            return 0

    # Create a new player window
    # ShuffleBot in <channel>
    # field: <track> value: <state>
    # footer: error message
    def __get_window(self, player: Player, err=None) -> discord.Embed:
        embed = discord.Embed()

        if player is None:
            embed.set_author(
                name=('spinnin\' in channel: ' + player.voice_channel),
                icon_url=self.config.bot_icon
            )
            if err is None:
                err = 'unknown'
            embed.add_field(name='Error', value=err)

        else:
            embed.set_author(
                name=('spinnin\' in channel: ' + player.voice_channel),
                icon_url=self.config.bot_icon
            )
            if player.state == PlayerState.STOPPED:
                embed.add_field(name='none', value=player.state_string())
            else:
                embed.add_field(name=player.current[0], value=player.state_string())

            # error message if applicable
            if err is not None:
                embed.set_footer(text=('Error: ' + err))
            else:
                embed.set_footer(text=f'Type {self.config.bot_prefix}help if you\'re stuck')

        return embed

    # Update all of a Players windows
    # - bring active text channel's window to the bottom, edit the others
    # - on error, only update active window
    async def __update_windows(self, ctx, player: Player, text_channel_id: int, err=None) -> None:

        if player is None:
            print('shuffle error: no player to update windows')
            return

        if err is not None:
            print(f'shuffle error: {err}')

        text_channels = player.msg_ids
        for chan_id, msg_id in text_channels.items():
            
            # active text channel window
            if chan_id == text_channel_id:
                msg = await ctx.channel.fetch_message(msg_id)
                msg_found = msg is not None
                msg_latest = True

                # current window is not most recent message
                if msg_found:
                    async for msg_first in ctx.channel.history(limit=1):
                        if msg_first.id != msg.id:
                            msg_latest = False
                            await msg.delete()
                print(f'UPDATE WINDOW {msg_found=} {msg_latest=}')
                
                if msg_latest:
                    await msg.edit(content=None, embed=self.__get_window(player, err=err))
                else:
                    msg_new = await ctx.send(content=None, embed=self.__get_window(player, err=err))
                    player.msg_ids[text_channel_id] = msg_new.id
                

            # different text channel
            elif err is None:
                channel = self.bot.get_channel(chan_id)
                if channel is not None:
                    msg = await channel.fetch_message(msg_id)

                    # just edit messages in other channels
                    if msg is not None:
                        await msg.edit(embed=self.__get_window(player))


    # Update Player state and update windows
    async def __update_player_state(self, ctx, player: Player, state: PlayerState, text_channel_id: int) -> None:
        player.state = state
        await self.__update_windows(ctx, player, text_channel_id)

    # Commands
    # play
    @commands.command(help='Search online or paste a URL')
    async def play(self, ctx, *args):

        # TEMP - TODO still create player, don't download, error message formatting
        if len(args) < 1:
            print('no args')
            return

        # track title or URL
        arg = ''.join(args).strip()
        print(f'play: query is \'{arg}\'')

        # need a new downloader for each request to at minimum get online track name
        d = Downloader(self.config.audiodir, self.config.codec)

        # get voice channel
        target = ctx.author
        if target.voice != None and target.voice.channel != None:
            voice_channel = ctx.author.voice.channel
        else: # no voice channel, do nothing
            return

        # voice channel info
        channel_id = voice_channel.id
        channel_name = voice_channel.name

        # text channel info
        text_channel_id = ctx.channel.id
        msg = None


        # AUDIO PLAYER SETUP PART
        # new player for this audio channel
        if channel_id not in self.control.players:
            # TODO
            # check for existing message for this channel and delete it

            # new player window (message) and Player for this voice channel
            msg = await ctx.send('Creating player...')
            self.control.players[channel_id] = Player(
                msg.id,
                text_channel_id,
                self.config.audiodir,
                channel_name # audio channel name
            )
        
        # make sure this text channel has a window
        else:
            if text_channel_id not in self.control.players[channel_id].msg_ids:
                msg = await ctx.send('Adding player window...')
                self.control.players[channel_id].msg_ids[text_channel_id] = msg.id

        player = self.control.players[channel_id]


        # INFO AND CACHE CHECKING PART
        # get the track title
        title = None # online title
        vid_id = None # vid ID (download name)
        try:
            title, vid_id = await d.get_title(arg) # await this since it blocks next steps
        except DownloadException as e:
            await self.__update_windows(ctx, player, text_channel_id, err='requested URL is bad')
        finally:
            if title is None:
                return
        
        # check cache for track
        in_cache = self.control.cache.contains(title)

        # queue track
        if player.push((title, in_cache)) is None: # track, cached?
            print('NO Q-ING')
            return
        await self.__update_windows(ctx, player, text_channel_id)


        # PLAYBACK PART
        if not in_cache:
            url = f'https://www.youtube.com/watch?v={vid_id}'
            # print('shuffle: downloading ' + url)
            d.download_video(url)
        
        # file extension, contatable
        ext = self.config.codec
        if ext[0] != '.':
            ext = '.' + ext
        
        # make sure the downloaded track is there, tell cache
        if os.path.isfile(self.config.audiodir + title + ext):
            self.control.cache.track_added(title)

        # if its not were screwed
        if not self.control.cache.contains(title):
            raise ShuffleBotException('downloaded file is not there')

        # join audio channel and play track
        ffmpeg_exe = self.config.ffmpegdir
        if ffmpeg_exe[-1] != '/':
            ffmpeg_exe += '/'
        ffmpeg_exe += self.config.ffmpegexe # bin/ffmpeg.exe
        print(f'ffmpeg: using {ffmpeg_exe}')
        print(f'source: {self.config.audiodir + title + ext}')

        # bot playin
        await self.__update_player_state(ctx, player, PlayerState.PLAYING, text_channel_id)
        vc = await voice_channel.connect()
        vc.play(discord.FFmpegPCMAudio(
            executable=ffmpeg_exe,
            source=self.config.audiodir + title + ext
        ))
        
        # keep playin
        while vc.is_playing() and player.state == PlayerState.PLAYING:
            sleep(.1)
        
        # make sure it's stopped now
        if player.state != PlayerState.STOPPED:
            await self.__update_player_state(ctx, player, PlayerState.STOPPED, text_channel_id)

        self.control.cache.track_finished(title) # track is removeable from cache
        await vc.disconnect()
        player.pop()

    # msg = await ctx.channel.fetch_message(self.control.players[])

    # stop
    @commands.command(help='Permanantly stop playback')
    async def stop(self, ctx):

        # get voice channel
        target = ctx.author
        if target.voice != None and target.voice.channel != None:
            voice_channel = ctx.author.voice.channel
        else: # no voice channel, do nothing
            return

        # channel info
        channel_id = voice_channel.id
        channel_name = voice_channel.name
        text_channel_id = ctx.channel.id

        if channel_id in self.control.players:
            p: Player = self.control.players[channel_id]
            await self.__update_player_state(ctx, p, PlayerState.STOPPED, text_channel_id)

    # pause
    @commands.command(help='Temporarily stop playback')
    async def pause(self, ctx):
        pass

    # resume
    @commands.command(help='Resume playback')
    async def resume(self, ctx):
        pass

    # skip
    @commands.command(help='Play next song in queue')
    async def skip(self, ctx):
        pass

    # list
    @commands.command(help='Show all saved playlists and tracks')
    async def list(self, ctx, arg=None):
        type = self.__arg_playlist_or_track(arg)

    # clear queue
    @commands.command(help='Clear the queue')
    async def clear(self, ctx, arg):
        pass

    # disconnect bot
    @commands.command(help='Disconnect bot from audio channel')
    async def disconnect(self, ctx, *args):
        pass

        # delete all its messages

        # stop playback and leave voice channel

        # delete Player 

    # Events
    # on ready
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Game(self.config.bot_isplaying))
        print(f'{self.bot.user} is connected using prefix {self.config.bot_prefix}')

    # on disconnect
    
