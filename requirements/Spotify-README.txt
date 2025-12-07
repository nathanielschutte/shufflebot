To setup spoofed Spotify music player, follow these steps:

1. Ensure discord.py is fully up to date. Also remember basics like running inside a virtual environment if that is where dependencies are installed.
    pip install -U discord.py
    python -m venv venv # create virtual environment (if not already created)
    source venv/bin/activate # adjust path as needed

2. Install Rust:
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    source $HOME/.cargo/env

3. Ensure you have all dependencies + ALSA dev headers
    sudo apt update
    sudo apt install -y libasound2-dev pkg-config

4. Install Librespot (Spotify client library):
    cargo install librespot --no-default-features --features "alsa-backend"

5. Generate credentials file for librespot (need to do special one time setup):
    a. mkdir -p /home/[your_username]/.cache/librespot # create cache directory

    b. /home/[your_username]/.cargo/bin/librespot -n "ShuffleBot" -b 320 --backend pipe --device /tmp/spotify_pipe -c /home/[your_username]/.cache/librespot # adjust path as needed

    c. Open Spotify app on your phone / pc (has to be on local network) and connect to "ShuffleBot" device to login and authorize. 
        Once connected, you should see log output in terminal indicating successful login and token generation. 
        Stop the process after successful login (Ctrl + C)
    
    d. Run the music bot. It will generate a website link for you to visit to complete the authorization process.
        YOU WILL GET AN ERROR IN BROWSER (this is what you want): This site can’t be reached...127.0.0.1 refused to connect.
        Copy the entire URL and paste it into the terminal where the bot is running to complete the authorization.

6. Create audio pipe for librespot to output into discord bot:
    mkfifo /tmp/spotify_pipe

7. Configure Spoify Developer Dashboard (use same account as the one used in librespot):
    - Go to https://developer.spotify.com/dashboard/applications
    - Create a new application
    - Note down Client ID and Client Secret
    - Set Redirect URIs to  https://localhost:8888/callback
                            https://github.com/nathanielschutte/shufflebot/tree/master/shuffle
                            http://127.0.0.1:8888/callback
    - Set "APIs used" to Web API, Web Playback SDK

8. Update .env file with your Spotify credentials:
    DISCORD_BOT_TOKEN=your_token_here
    SPOTIFY_CLIENT_ID=your_client_id
    SPOTIFY_CLIENT_SECRET=your_client_secret
    SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback

9. Start spoofed device with librespot (use dedicated separate spotify account / user on family plan to avoid issues)
NOTE: Needs to be running in background for bot to work (recommended to setup as systemd service, SEE librespot.service.txt)
    /home/[your_username]/.cargo/bin/librespot -n "ShuffleBot" -b 320 --backend pipe --device /tmp/spotify_pipe -c /home/[your_username]/.cache/librespot

10. Start the bot:
    python bot.py


# Helpful commands for managing librespot service:
    # Check status:
         sudo systemctl status librespot
    # Restart service:
         sudo systemctl restart librespot
    # View logs:
         sudo journalctl -u librespot -f




