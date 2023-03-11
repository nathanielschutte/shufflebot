[![Tests](https://github.com/nathanielschutte/shufflebot/actions/workflows/test.yml/badge.svg)](https://github.com/nathanielschutte/shufflebot/actions/workflows/test.yml)

# shufflebot

Queue up songs to play in discord voice channels with search queries

## Run

### Configure
Create a .env based on .env.example and set the discord token DISCORD_BOT_TOKEN
Set SHUFFLE_ENV to `local` to log to `out.log` in the current directory

### Build
```
make build
```

### Run editable container locally
```
make run-dev
python bot.py
```

### Run server
```
make run
```
