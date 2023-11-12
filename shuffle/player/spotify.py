
import os
import spotipy # type: ignore
import json

from shuffle.player.stream import Stream
from shuffle.player.models.Track import Track
from shuffle.log import shuffle_logger

class SpotifyStream(Stream):
    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)

        self.logger = shuffle_logger('spotify')

        self.username = os.getenv('SPOTIFY_USERNAME')
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_url = os.getenv('SPOTIFY_REDIRECT_URL')

        self.ready = False
        self._setup()

    def _setup(self) -> None:
        if self.guild_id not in [486252937354543104]:
            raise NotImplementedError('Spotify is only supported for whitelisted servers')

        oauth_object = spotipy.SpotifyOAuth(self.client_id, self.client_secret, self.redirect_url) 
        token_dict = oauth_object.get_access_token() 
        token = token_dict['access_token'] 
        spotify = spotipy.Spotify(auth=token)
        user_name = spotify.current_user()

        print(json.dumps(user_name, sort_keys=True, indent=4)) 

    def download(self, video_hash: str, path: str) -> None:
        raise NotImplementedError('Spotify does not support downloading')
    
    def get_track(self, query: str) -> Track:
        ...

    def is_ready(self) -> bool:
       return self.ready
