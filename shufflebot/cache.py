
# Cache of audio files, tracks space usage and download order

import os

# Store track name, age, and usage status
TrackEntry = tuple[str, int, bool]

class Cache:

    def __init__(self, dir, capacity=0, ext='.mp3') -> None:
        
        # Stored tracks
        self.tracks = []

        if dir[-1] != '/':
            dir += '/'
        self.dir = dir

        if ext[0] != '.': # concatable
            ext = '.' + ext
        self.ext = ext

        self.used = 0 # MB
        self.capacity = int(capacity) # MB
        self.latest = 0

        self.load_current()

    # See what's already in audio cache
    def load_current(self):
        for file in os.listdir(self.dir):
            if file.endswith( self.ext):
                print('cache: discovered existing file ' + file)
                self.track_added(os.path.splitext(file)[0])

    # Check if cache contains track
    def contains(self, title):
        if len(self.tracks):
            for track in self.tracks:
                if track[0] == title:
                    return True
        return False

    # Indicate mp3 added to directory
    def track_added(self, title):

        # already have this track for some reason
        had_it = False
        if self.contains(title):
            idx = 0
            for track in self.tracks:
                if track[0] == title:
                    # just make it "in use"
                    updated_track = (track[0], track[1], True)
                    self.tracks[idx] = updated_track
                    had_it = True
                    print('cache: resetting discovered track ', updated_track)
                idx += 1

        # get file size
        size = 0
        if os.path.isfile(self.dir + title + self.ext):
            size = os.path.getsize(self.dir + title + self.ext)
            size /= (1024 * 1024) # B -> MB
        else:
            return
        #print(self.dir + title, size)

        # clear out old tracks until there's space
        if not had_it:
            rm_success = True
            while rm_success and len(self.tracks) > 0 and not self.__check_size(size):
                rm_success = self.__remove_oldest()

            # only track, if there is no space, no luck
            if not self.__check_size(size):
                print('cache: trying to add a file that is too big!!! skipping')
                return

        # track add
        self.tracks.append((title, self.latest, True)) # True = in use
        self.used += size
        self.latest += 1
        print(f'cache: added file, using {self.used:.2f}/{self.capacity} MBs')

        

    # Indicate mp3 finished playback
    def track_finished(self, title):
        if len(self.tracks):
            idx = 0
            for track in self.tracks:
                if track[0] == title:
                    # make track removeable
                    updated_track = (track[0], track[1], False)
                    self.tracks[idx] = updated_track
                idx += 1


    # Enough space?
    def __check_size(self, spec):
        print(f'cache: checking usage {(self.used):.2f}/{self.capacity} adding {spec:.2f}')
        return (self.capacity - self.used - spec) >= 0

    # Trash the oldest track
    def __remove_oldest(self):
        oldest = self.latest
        rm_idx = -1
        idx = 0

        for entry in self.tracks:

            # track must be idle, and old
            if not entry[2] and entry[1] < oldest:
                oldest = entry[1]
                rm_idx = idx
            idx += 1
            
        # at least one track
        if rm_idx >= 0:
            print(f'cache: removing track {self.tracks[rm_idx][0]} from cache, age {self.latest - oldest}')
            del self.tracks[rm_idx]

            # rm file
            if os.path.exists(self.dir + self.tracks[rm_idx][0]):
                rm_size = os.path.getsize(self.dir + self.tracks[rm_idx][0])
                os.remove(self.dir + self.tracks[rm_idx][0])
                self.used -= rm_size

                print(f'cache: removed file, using {self.used:.2f}/{self.capacity} MBs')
                return True

            else:
                print(f'cache: could not find file {self.dir + self.tracks[rm_idx][0]}')
                return False

        # either empty or none removeable
        else:
            print(f'cache: could not remove any tracks, they might be in use')
            return False