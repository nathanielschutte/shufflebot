
# ConfigReader
class ConfigReader:
    """.ini file reader"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.config = {}

    def read(self, path):
        file = None
        try:
            file = open(path, 'r')
            lines = file.readlines()
            group = ''

            for line in lines:
                line.strip()
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

    # Get a config value, can specify datatype
    def get(self, group, key, fallback, type=object):
        if group in self.config:
            if key in self.config[group]:
                return self.config[group][key]
        return fallback

    # Get dict of all config values in group
    def getGroup(self, group):
        if group in self.config:
            return self.config[group]
        else:
            return False
        