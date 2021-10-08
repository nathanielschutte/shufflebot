
# Aliases

import os

# Config read (using util) to constants
class Aliases:
    """Holds a config state"""

    def __init__(self, file):
        self.file = file

        # try file
        # fallback to default file
        # error

# Config defaults for fallback values
class AliasesFallback:
    aliases_file = 'config/aliases'
    aliases = {}