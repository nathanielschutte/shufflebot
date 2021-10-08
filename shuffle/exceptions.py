

class ShuffleBotException(Exception):
    def __init__(self, msg, *args) -> None:
        super().__init__(msg)
        self._msg = msg
    
    @property
    def message(self):
        return self._msg

class ConfigException(ShuffleBotException):
    pass

class FFmpegException(ShuffleBotException):
    pass

class DownloadException(ShuffleBotException):
    pass

class FormattedException(ShuffleBotException):
    def __init__(self, error, *args, header='ShuffleBot error:') -> None:
        self.error = error
        self.header = header
        self.format = '{header}\n{error}\n'
    
    @property
    def message(self):
        return self.format.format(header = self.header, error = self.error)