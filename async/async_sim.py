import asyncio
import traceback

# Represents audio file store in file system
# [track name, downloading?]
TrackStore = dict[str, bool]
cache: TrackStore = {}

# Need a small amount of output clarity
filters = []
screens = []
def log(group, message):
    if len(filters) > 0:
        if not group in filters:
            return
    if len(screens) > 0:
        if 'SCREEN' in group and not group in screens:
            return
    print(f'[{group}] {message}')



# Simulate two fetch tasks:
# 1. getting the title of the query result
# 2. downloading the file
# Way more involved in the actual thing
class Downloader():

    def __init__(self) -> None:
        pass

    @staticmethod
    async def fetch_title(query):
        log('download', f'Fetching title for {query}...')
        await asyncio.sleep(2)
        title = '@' + query # distinguish
        log('download', f'Title for {query} is {title}')
        return title

    @staticmethod
    async def download(title):
        log('download', f'Downloading title {title}...')
        await asyncio.sleep(4)
        log('download', f'Download compelete for {title}' )



# A player exists for each audio channel that has a user requesting playback:
# Each player has a queue, and handles async fetch actions
# Each player has a running playback loop that handles joining and leaving the audio channel,
#   moving through the queue, and paying attention to the player state (play, stop, etc.)

# A track is stored with [its unique title, its download status]
Track = list[str, bool]

class Player():

    def __init__(self, id=None, loop=None, runner=None, bot=None) -> None:
        self._queue: list[Track] = []        # Song queue
        self.current = None
        self.state = 'idle'
        self.connected = False
        self.loaded_track = None
        self.loaded_track_downloaded = False
        self.exist = True
        self.loop = loop        # event loop
        self.runner: Runner = runner
        self.bot: Bot = bot
        self.id = id            # audio channel id
        self.channel_id = id    # would be array of text channels
        self.in_playback = False

        # screen status event
        self.events = Events()
        self.events.on('status', self.bot.screen)


    # Queue track
    async def queue(self, track):

        # get title first - this is because multiple queries may resolve to the same 1st search result
        log('queue', 'Getting title...')
        title = await Downloader.fetch_title(track)
        log('queue', 'Got title')

        # check cache
        cached = title in cache
        self._queue.append([title, cached])
        #print(self._queue)
        
        # start the download if needed
        if not cached:
            log('queue', 'Not cached, downloading...')
            cache[title] = title # cache now so that an identical query will know this title is being downloaded
            await Downloader.download(title)
            # handle download failure here and remove from cache
            # look for identical queries and remove them from queue or restart their downloads?
            log('queue', 'Download finished, updating queue status...')

             # track is loaded already and waiting
            if self.loaded_track == title:
                self.loaded_track_downloaded = True
                log('queue', 'Status updated in current')
            else:
                log('queue', 'Error, cannot find track to update download status')

            # track sitting in queue - still check this in case of dupe queries
            for t in self._queue:
                if t[0] == title:
                    t[1] = True # set download status to true
                    log('queue', 'Status updated in queue')
        else:
            log('queue', 'Already cached, done')

    # Get next track from queue
    def pop(self):
        if len(self._queue) > 0:
            self.loaded_track = self._queue[0][0]
            self.loaded_track_downloaded = self._queue[0][1]
            self._queue = self._queue[1:]
        if self.loaded_track is not None:
            return self.loaded_track

    # Status control updates
    def set_status(self, status):
        if status == 'play':
            self.status = 'play'
        elif status == 'stop':
            self.status = 'stop'

    # Screen updates
    # Would emit status event for each text channel ID
    def __screen_updates(self, status):
        events = self.events
        events.emit('status', channel_id=self.id, status={'status': status})

    # Playback task
    async def start(self):
        self.in_playback = True

        log('playback', 'Starting playback loop...')
        while self.exist:

            # idle until something is queued
            if len(self._queue) == 0:
                if self.state != 'stop': # if the player state was set to stop, stay stopped
                    self.state = 'idle'
                    self.__screen_updates(self.state)

            # wait until there's a track queued up and playback isn't stopped
            stop_timeout = 0
            while self.exist and ((self.state == 'idle' and len(self._queue) == 0) \
                or self.state == 'stop'):
                
                # if stopped or nothing queued, timeout after 20 seconds
                stop_timeout += 1
                if stop_timeout > 200:
                    if self.connected:
                        self.connected = False # disconnect from voice channel
                    self.exist = False # gtfo
                    break

                await asyncio.sleep(0.1)

            # meant to end the playback loop
            if not self.exist:
                break
            
            # get next queued song
            self.pop()

            # wait for download to finish
            if not self.loaded_track_downloaded:
                self.state = 'waiting'
                self.__screen_updates(self.state)
            while self.exist and not self.loaded_track_downloaded:
                await asyncio.sleep(0.1)
            
            # make sure the cache is right and loaded track is ready to go
            if self.loaded_track not in cache:
                log('PLAYBACK ERROR', 'track file missing')
                continue

            # double check that the cache is accurate, if the file is missing abort on this track

            if self.state != 'play':
                self.state = 'play' # make sure state is right
                self.__screen_updates(self.state + ': ' + self.loaded_track)
            if self.connected == False:
                self.connected = True # connect to the voice channel

            # play track
            is_playing = True
            duration = 60 # 6 s
            log('playback', f'Playing {self.loaded_track}')
            while self.state == 'play' and is_playing:
                duration -= 1
                await asyncio.sleep(0.1)
                if duration <= 0: # track ends normally
                    is_playing = False
            log('playback', f'Finished playing {self.loaded_track}')

            if self.state == 'stop': # direct state change to stop playback early
                self.__screen_updates(self.state)

        self.in_playback = False
        log('playback', 'Stopped playback loop.')

        # this player will need to be restarted
                

# Pretend it's a discord Cog
class Bot():

    def __init__(self, runner) -> None:
        self.runner = runner

    # represents async nature of screen updates
    async def screen(self, channel_id, status):
        if status and 'status' in status:
            await asyncio.sleep(0.5)
            log(f'SCREEN {channel_id}', status['status'])

    # Command play
    async def play(self, channel_id, query):
        loop = self.runner.loop

        # get a player going
        if not channel_id in self.runner.players:
            self.runner.players[channel_id] = Player(id=channel_id, loop=loop, runner=self.runner, bot=self)

        # current active player
        player: Player = self.runner.players[channel_id]
        player.set_status('play')

        # start the main player playback loop
        if not player.in_playback:
            loop.create_task(self.runner.players[channel_id].start())

        # queue song requested
        loop.create_task(player.queue(query))

        log('command', 'Done executing play')

    # Command stop
    async def stop(self, channel_id):

        # if player exists, stop playback
        if channel_id in self.runner.players:
            player: Player = self.runner.players[channel_id]

            player.set_status('stop')

        log('command', 'Done executing stop')

    # Command kill
    async def kill(self):
        log('command', 'Killing...')
        self.runner.exist = False

            

# The runner tracks additional state stuff outside of the discord Cog
class Runner():

    def __init__(self) -> None:
        self.players = {}       # one player per audio channel ID
        self.bot = Bot(self)    # one bot
        self.loop = None        # store asyncio event loop
        self.exist = True

    async def start(self, loop):
        self.loop = loop
        log('runner', 'Starting...')

        while self.exist:
            await asyncio.sleep(0.1)


        log('runner', 'Main event loop ending...')


# Simulate some incoming connections
async def sim(runner):
    await asyncio.sleep(1)

    # channel_id will really be passed by discord context
    # query can also be a URL
    # play(channel_id, query)
    await runner.bot.play(0, 'fireflies')
    await asyncio.sleep(1)

    # different channel, different player, but should share cached tracks
    await runner.bot.play(1, 'fireflies')
    await asyncio.sleep(2)

    await runner.bot.play(1, 'ACDC - Back in Black')
    
    await runner.bot.stop(0)

    await asyncio.sleep(1)
    
    # duplicate calls should have download updates all resolve at once
    # await runner.bot.play(0, 'fireflies')
    # await runner.bot.play(0, 'fireflies')
    # await runner.bot.play(0, 'fireflies')


def main():
    loop = asyncio.get_event_loop()
    runner = Runner()

    # start two tasks: the bot, and the incoming client commands
    loop.run_until_complete(asyncio.gather(runner.start(loop), sim(runner)))



# Concept found online - not sure how applicable yet
class Events:
    def __init__(self) -> None:
        self.events = {}
        self.loop = asyncio.get_event_loop()

    def emit(self, event, *args, **kwargs):
        if event not in self.events:
            return

        for callback in list(self.events[event]):
            try:
                if asyncio.iscoroutinefunction(callback):
                    self.loop.create_task(callback(*args, **kwargs))
                else:
                    callback(*args, **kwargs)
            except:
                traceback.print_exc()
    
    def on(self, event, callback):
        if event not in self.events:
            self.events[event] = []
        self.events[event].append(callback)
        return self
    
    def off(self, event, callback):
        if event not in self.events:
            return
        self.events[event].remove(callback)

        if not self.events[event]:
            del self.events

        return self

    def once(self, event, callback):
        def _callback(*args, **kwargs):
            self.off(event, _callback)
            return callback(*args, **kwargs)

        return self.on(event, _callback)



if __name__ == '__main__':
    main()