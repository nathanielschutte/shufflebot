
# Aliases

import os

class Aliases:
    """Command aliases"""

    def __init__(self, file):
        self.file = file

# Config defaults for fallback values
class AliasesFallback:
    aliases_file = 'config/aliases'
    aliases = {}