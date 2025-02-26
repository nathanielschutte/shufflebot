REMOTE_HOST=bot
REMOTE_USER=deploy-user
REMOTE_PATH=/var/www/code/bots/shuffle

if ! ssh $REMOTE_HOST "sudo mkdir -p $REMOTE_PATH && sudo chown $REMOTE_USER.$REMOTE_USER $REMOTE_PATH && sudo chmod 2775 $REMOTE_PATH"; then
    echo "Error creating remote path"
    exit 1
fi

if ! rsync -rvz --exclude-from=.deploy/rsync-exclude.txt . $REMOTE_HOST:$REMOTE_PATH; then
    echo "Error rsyncing files"
    exit 1
fi

if ! ssh $REMOTE_HOST "sudo chown -R $REMOTE_USER.$REMOTE_USER $REMOTE_PATH && sudo chmod -R 2775 $REMOTE_PATH"; then
    echo "Error changing permissions"
    exit 1
fi

docker_ps=$(ssh $REMOTE_HOST "sudo -u $REMOTE_USER docker ps -a | grep shuffle:latest | cut -d ' ' -f1")
if [ $? -ne 0 ]; then
    echo "Error getting docker ps"
    exit 1
fi

if [ ! -z "$docker_ps" ]; then
    # removes container since it ran with --rm
    if ! ssh $REMOTE_HOST "sudo -u $REMOTE_USER docker stop $docker_ps"; then
        echo "Error stopping docker container"
        exit 1
    fi
fi

if ! ssh $REMOTE_HOST "cd $REMOTE_PATH && sudo -u $REMOTE_USER make run"; then
    echo "Error running server"
    exit 1
fi
