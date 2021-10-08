
# Run bot, catch dependency errors

import shuffle

def main() -> int:
    
    try:
        bot = shuffle.bot(config_file='config/config.ini', aliases_file='config/aliases.json')
        bot.run()
        
    except:
        return -1

if __name__ == '__main__':
    print('ShuffleBot exited with code', main())