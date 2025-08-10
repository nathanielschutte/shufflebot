#!/usr/bin/env python3
"""
Test if Discord voice works with a local audio file
This bypasses YouTube/network issues
"""

import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# Load token
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    print("Error: DISCORD_BOT_TOKEN not found in .env")
    exit(1)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot ready as {bot.user}')
    print('Commands: !test, !join, !leave')

@bot.command()
async def test(ctx):
    """Test voice connection with a generated tone"""
    
    # Check if user is in voice channel
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel!")
        return
    
    channel = ctx.author.voice.channel
    await ctx.send(f"Joining {channel.name}...")
    
    try:
        # Connect to voice
        print(f"Connecting to {channel.name}...")
        voice = await channel.connect(timeout=10.0)
        print(f"Connected! is_connected={voice.is_connected()}")
        
        await ctx.send("Connected! Generating test audio...")
        
        # Generate a test audio file using FFmpeg
        import subprocess
        
        # Create a 5-second test tone
        test_file = "test_audio.mp3"
        
        print("Generating test audio file...")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'sine=frequency=440:duration=5',
            '-ar', '48000',
            '-ac', '2',
            test_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        
        if result.returncode != 0:
            await ctx.send("Failed to generate test audio")
            print(f"FFmpeg error: {result.stderr}")
            await voice.disconnect()
            return
        
        print(f"Test file created: {test_file}")
        
        # Play the test file
        await ctx.send("Playing test tone (440 Hz for 5 seconds)...")
        
        try:
            # Try to play
            print("Attempting to play audio...")
            audio_source = discord.FFmpegPCMAudio(test_file)
            
            voice.play(audio_source, after=lambda e: print(f'Playback finished: {e}'))
            
            print("Play command sent")
            await ctx.send("✓ Playing test tone!")
            
            # Wait for playback to finish
            while voice.is_playing():
                await asyncio.sleep(0.5)
            
            await ctx.send("Test complete!")
            
        except discord.ClientException as e:
            await ctx.send(f"Failed to play: {e}")
            print(f"Play error: {e}")
        
        # Clean up
        await asyncio.sleep(1)
        await voice.disconnect()
        
        # Delete test file
        try:
            os.remove(test_file)
        except:
            pass
        
    except asyncio.TimeoutError:
        await ctx.send("Connection timed out!")
        print("Connection timeout")
    except Exception as e:
        await ctx.send(f"Error: {e}")
        print(f"Error: {e}")

@bot.command()
async def join(ctx):
    """Just join voice channel"""
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel!")
        return
    
    channel = ctx.author.voice.channel
    
    try:
        voice = await channel.connect(timeout=10.0)
        await ctx.send(f"Joined {channel.name}")
        print(f"Joined. is_connected={voice.is_connected()}")
        
        # Wait a bit then report status
        await asyncio.sleep(2)
        await ctx.send(f"Connection status: {voice.is_connected()}")
        
    except Exception as e:
        await ctx.send(f"Failed to join: {e}")
        print(f"Join error: {e}")

@bot.command()
async def leave(ctx):
    """Leave voice channel"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected")
    else:
        await ctx.send("Not connected to voice")

# Run bot
print("Starting test bot...")
print("Use !test in a Discord channel while in voice")
bot.run(TOKEN)