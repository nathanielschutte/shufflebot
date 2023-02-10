
# ConfigReader
class ConfigReader:
    """Low grade .ini file reader"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.config = {}

    # Load config file
    def read(self, path):
        file = None
        try:
            file = open(path, 'r')
            lines = file.readlines()
            group = ''

            for line in lines:
                line.strip()

                # Ignore anything after #
                commentIdx = line.find('#')
                if commentIdx != -1:
                    if commentIdx == 0:
                        continue
                    line = line[:line.find('#')]
                
                # Set the current group
                if line[0] == '[' and line.find(']') != -1:
                    group = line[1:line.find(']')].strip()

                
                else:
                    if len(line.strip()) > 0:
                        delim = line.find('=')
                        key = line[:delim].strip()
                        val = line[delim+1:].strip().replace('\'', '').replace('\"', '')
                        if self.verbose:
                            print(f'config: [{group}] {key} = {val}')
                        if not group in self.config:
                            self.config[group] = {}
                        self.config[group][key] = val
                        
        except:
            print('config: error reading ' + path)

        finally:
            if file != None and not file.closed:
                file.close()

    # Get a config value as a string
    def get(self, group, key, fallback):
        if group in self.config:
            if key in self.config[group]:
                return self.config[group][key]
        return fallback

    # Convert config value to bool
    def get_bool(self, group, key, fallback):
        if type(fallback) != bool:
            fallback = False
        if group in self.config:
            if key in self.config[group]:
                val: str = self.config[group][key].lower()
                if val == 'true' or val == 't' or val == 1:
                    return True
                elif val == 'false' or val == 'f' or val == 0:
                    return False
                return fallback
        return fallback

    # Convert config value to int
    def get_int(self, group, key, fallback):
        pass

    # Get dict of all config values in group
    def get_group(self, group):
        if group in self.config:
            return self.config[group]
        else:
            return False
        