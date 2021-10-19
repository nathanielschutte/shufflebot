
# Aliases

import os

# Command aliases
class Aliases:
    """Bot command aliases"""

    def __init__(self, file):
        self.file = file

# Defaults
class AliasesFallback:
    aliases_file = 'config/aliases.json'
    aliases = {}