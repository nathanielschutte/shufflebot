# CONFIG
config = {}

# [section]
# key=value
def readConfig(path, speak):
    global config
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
                    if speak:
                        print(f'config: [{group}] {key} = {val}')
                    if not group in config:
                        config[group] = {}
                    config[group][key] = val
    except:
        print('config: error reading ' + path)
    finally:
        if file != None and not file.closed:
            file.close()
    return config

def getConfig(group, key):
    if group in config:
        if key in config[group]:
            return config[group][key]
    return False

def getConfigGroup(group):
    if group in config:
        return config[group]
    else:
        return False
        