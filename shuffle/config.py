
import os

# Config read (using util) to constants
class Config:
    """Holds a config state"""

    def __init__(self, file):
        self.file = file

        # try file
        # fallback to default file
        # error

    # check config values
    def config_checks():
        pass

    # check if config is missing any values in config_template.ini
    def config_diff():
        template_path = 'config/config_template.ini'

# Config defaults for fallback values
class ConfigFallback:
    config_file = 'config/config.ini'
    aliases_file = 'config/aliases.json'