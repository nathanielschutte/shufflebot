import asyncio
import time
import os
import sys

class RebootException(Exception):
    ...

async def run_task():
    await asyncio.sleep(1)
    print('task')
    await asyncio.sleep(1)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def main():
    await asyncio.sleep(1)
    task = asyncio.create_task(run_task())
    await task
    exception = task.exception()
    print(exception)
    # if exception is RebootException:
    #     print('reboot signal')
    #     raise RebootException

while True:
    try:
        loop.run_until_complete(main())
    except RebootException as e:
        print(f'reboot because {e}')
        time.sleep(2)
