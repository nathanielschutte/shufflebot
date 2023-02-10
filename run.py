
# Run bot, catch dependency errors

import os, sys
import time
from dotenv import load_dotenv

verbose = '-v' in sys.argv

def log(message):
    if verbose:
        print(message)

def check_environment() -> None:
    print('Checking bot environment...')

    # These directories need to be here to run bot
    try:
        assert os.path.isdir('config'), 'cannot find dir "config"'
        assert os.path.isdir('storage'), 'cannot find dir "storage"'
        assert os.path.isdir('shufflebot'), 'cannot find dir "shufflebot"'
    except AssertionError as e:
        log(f'Failed environment check: {e}')

    log('Environment OK')

def main() -> int:

    load_dotenv()
    if (os.getenv('DEV') == '1'):
        from shufflebot import ShuffleBot
        bot = ShuffleBot()
        return bot.run()

    # Startup checks
    check_environment()
    
    pip_requirements = False # checked requirements yet?
    keep_trying = True # should keep trying to start bot?

    retry_wait_time = 4 # seconds
    max_tries = 3 # retries till failure
    tries = 0

    while keep_trying:
        bot = None
        code = -1
        try:
            from shufflebot import ShuffleBot
            bot = ShuffleBot()
            code = bot.run()
        
        # Better go and fix these
        except (AttributeError, SyntaxError, NameError) as e:
            log(f'Code error: {e}')
            break

        # Look for custom exceptions
        except Exception as e:
            log(e.__class__.__name__)
            if hasattr(e, '__module__') and e.__module__ == 'shufflebot.exceptions':
                if e.__class__.__name__ == 'FormattedException':
                    log(e.message)
                    break
                else:
                    log('Error type ' + e.__class__.__name__)
            else:
                log(f'Unknown error: {e}')
        
        # Dependency issue, try to upgrade pip with requirements.txt
        except ImportError:

            # try upgrading with pip
            if pip_requirements:
                pip_requirements = True

                # upgrade pip
            
            # already tried upgrading, something else is wrong
            else:
                break

        finally:
            if code != 1:
                tries += 1
            else:
                keep_trying = False

            if tries >= max_tries:
                log('Restarts exceeded, exiting...')
                break
            elif keep_trying and bot is not None:
                log(f'Restarting in {retry_wait_time} seconds...')
                time.sleep(retry_wait_time)
            else:
                return code
    
    # if retry loop broken
    return -1

if __name__ == '__main__':
    log('ShuffleBot exited with code', main())