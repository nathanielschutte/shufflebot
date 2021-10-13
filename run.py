
# Run bot, catch dependency errors

import os
import time
from dotenv import load_dotenv

def check_environment() -> None:
    print('Checking bot environment...')

    # These directories need to be here to run bot
    try:
        assert os.path.isdir('config'), 'cannot find dir "config"'
        assert os.path.isdir('storage'), 'cannot find dir "storage"'
        assert os.path.isdir('shufflebot'), 'cannot find dir "shufflebot"'
    except AssertionError as e:
        print(f'Failed environment check: {e}')

    print('Environment OK')

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
            print(f'Code error: {e}')
            break

        # Look for custom exceptions
        except Exception as e:
            print(e.__class__.__name__)
            if hasattr(e, '__module__') and e.__module__ == 'shufflebot.exceptions':
                if e.__class__.__name__ == 'FormattedException':
                    print(e.message)
                    break
                else:
                    print('Error type ' + e.__class__.__name__)
            else:
                print(f'Unknown error: {e}')
        
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
                print('Restarts exceeded, exiting...')
                break
            elif keep_trying and bot is not None:
                print(f'Restarting in {retry_wait_time} seconds...')
                time.sleep(retry_wait_time)
            else:
                return code
    
    # if retry loop broken
    return -1

if __name__ == '__main__':
    print('ShuffleBot exited with code', main())