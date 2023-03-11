REMOTE_HOST=bot
REMOTE_PATH=/var/www/code/bots/shuffle_test

rsync -avz --exclude-from=.deploy/rsync-exclude.txt . $REMOTE_HOST:$REMOTE_PATH
