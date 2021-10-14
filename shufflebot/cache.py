
# Cache of audio files, tracks space usage and download order

import os

# Store track name, age, and usage status
TrackEntry = tuple[str, int, bool]

class Cache:

    def __init__(self, dir) -> None:
        
        # Stored tracks
        self.tracks = []

        if dir[-1] != '/':
            dir += '/'
        self.dir = dir

        self.used = 0 # MB
        self.capacity = 100 # MB
        self.latest = 0

    # Check if cache contains track
    def contains(self, title):
        if len(self.tracks):
            for track in self.tracks:
                if track[0] == title:
                    return True
        return False

    # Indicate mp3 added to directory
    def track_added(self, title, size):
        if self.__check_size(size):
            self.tracks.append((title, self.latest, True)) # True = in use
            self.used += size
            self.latest += 1
        else:
            self.__remove_oldest()

    # Indicate mp3 finished playback
    def track_finished(self, title):
        if len(self.tracks):
            for track in self.tracks:

                # have track
                if track[0] == title:
                    track[2] = False # now removeable


    # Enough space?
    def __check_size(self, spec):
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
                os.remove(self.dir + self.tracks[rm_idx][0])
            else:
                print(f'cache: could not find file {self.dir + self.tracks[rm_idx][0]}')

        # either empty or none removeable
        else:
            print(f'could not remove any tracks, they might be in use')