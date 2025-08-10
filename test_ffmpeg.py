#!/usr/bin/env python3
"""
Test script to verify FFmpeg and Discord voice functionality
Run this from your shufflebot directory: python test_ffmpeg.py
"""

import subprocess
import sys
import os
import asyncio
import discord
from discord.ext import commands

def test_ffmpeg():
    """Test if FFmpeg is installed and accessible"""
    print("=" * 60)
    print("TESTING FFMPEG")
    print("=" * 60)
    
    # Test ffmpeg command
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            print(f"✓ FFmpeg found: {lines[0]}")
            
            # Check for important codecs
            if 'libopus' in result.stdout:
                print("✓ Opus codec available")
            else:
                print("⚠ Opus codec might not be available")
                
            if 'libmp3lame' in result.stdout:
                print("✓ MP3 codec available") 
            else:
                print("⚠ MP3 codec might not be available")
                
        else:
            print(f"✗ FFmpeg returned error code {result.returncode}")
            print(f"Error output: {result.stderr}")
            
    except FileNotFoundError:
        print("✗ FFmpeg not found in PATH!")
        print("\nTo install FFmpeg on Windows:")
        print("1. Download from: https://www.gyan.dev/ffmpeg/builds/")
        print("2. Extract to C:\\ffmpeg")
        print("3. Add C:\\ffmpeg\\bin to your PATH environment variable")
        print("4. Restart PowerShell/Command Prompt")
        return False
        
    except subprocess.TimeoutExpired:
        print("✗ FFmpeg command timed out")
        return False
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    
    # Test ffmpeg with a simple conversion (create a test file)
    print("\nTesting FFmpeg functionality...")
    try:
        # Create a simple test to see if ffmpeg can process audio
        test_cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=1',
            '-f', 'null', '-', '-y'
        ]
        
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            timeout=5,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ FFmpeg can process audio")
        else:
            print(f"⚠ FFmpeg audio processing returned error: {result.stderr[:200]}")
            
    except Exception as e:
        print(f"⚠ Could not test FFmpeg audio processing: {e}")
    
    return True

def test_python_packages():
    """Test if required Python packages are installed"""
    print("\n" + "=" * 60)
    print("TESTING PYTHON PACKAGES")
    print("=" * 60)
    
    packages = {
        'discord': discord.__version__ if 'discord' in sys.modules else None,
        'yt_dlp': None,
        'asyncio': 'built-in',
        'dotenv': None
    }
    
    # Try to import packages
    try:
        import yt_dlp
        packages['yt_dlp'] = yt_dlp.version.__version__
    except ImportError:
        pass
        
    try:
        import dotenv
        packages['dotenv'] = 'installed'
    except ImportError:
        pass
    
    all_good = True
    for pkg, version in packages.items():
        if version:
            print(f"✓ {pkg}: {version}")
        else:
            print(f"✗ {pkg}: NOT INSTALLED")
            all_good = False
            
    if not all_good:
        print("\nInstall missing packages with:")
        print("pip install discord.py yt-dlp python-dotenv")
        
    return all_good

def test_network():
    """Test network connectivity to Discord and YouTube"""
    print("\n" + "=" * 60)
    print("TESTING NETWORK")
    print("=" * 60)
    
    import urllib.request
    import urllib.error
    
    tests = [
        ("Discord API", "https://discord.com/api/v10"),
        ("YouTube", "https://www.youtube.com"),
        ("Google Video", "https://googlevideo.com")
    ]
    
    for name, url in tests:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                print(f"✓ {name}: Reachable (Status: {response.status})")
        except urllib.error.HTTPError as e:
            if e.code in [400, 401, 403, 404]:
                # These are expected for API endpoints
                print(f"✓ {name}: Reachable (Status: {e.code})")
            else:
                print(f"⚠ {name}: HTTP Error {e.code}")
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {str(e)[:50]}")

async def test_discord_voice():
    """Test Discord voice functionality"""
    print("\n" + "=" * 60)
    print("TESTING DISCORD VOICE (Basic)")
    print("=" * 60)
    
    # Check if opus is available
    if discord.opus.is_loaded():
        print("✓ Discord Opus library is loaded")
    else:
        print("✗ Discord Opus library is NOT loaded")
        print("  Trying to load opus...")
        
        # Try to load opus
        try:
            # Common opus library names on Windows
            opus_libs = [
                'opus',
                'libopus-0',
                'libopus',
                'C:\\Windows\\System32\\opus.dll'
            ]
            
            loaded = False
            for lib in opus_libs:
                try:
                    discord.opus.load_opus(lib)
                    if discord.opus.is_loaded():
                        print(f"  ✓ Loaded opus from: {lib}")
                        loaded = True
                        break
                except:
                    continue
                    
            if not loaded:
                print("  ✗ Could not load opus library")
                print("\n  To fix on Windows:")
                print("  1. Download opus from: https://opus-codec.org/downloads/")
                print("  2. Place opus.dll in C:\\Windows\\System32")
                print("  OR")
                print("  Install with: pip install discord.py[voice]")
        except Exception as e:
            print(f"  ✗ Error loading opus: {e}")

def test_youtube_extraction():
    """Test if yt-dlp can extract YouTube URLs"""
    print("\n" + "=" * 60)
    print("TESTING YOUTUBE EXTRACTION")
    print("=" * 60)
    
    try:
        import yt_dlp
        
        print("Testing yt-dlp extraction (this may take a few seconds)...")
        
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                # Test with a short, stable video
                info = ydl.extract_info("ytsearch:test video 10 seconds", download=False)
                
                if info and 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                    print(f"✓ Can search YouTube")
                    print(f"  Found: {entry.get('title', 'Unknown')[:50]}...")
                    
                    # Try to get formats
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    video_info = ydl.extract_info(video_url, download=False)
                    
                    if 'formats' in video_info:
                        print(f"✓ Can extract video formats ({len(video_info['formats'])} formats found)")
                    
                    if 'url' in video_info or ('formats' in video_info and video_info['formats']):
                        print("✓ Can get playable URLs")
                    else:
                        print("⚠ Could not get playable URLs")
                else:
                    print("✗ YouTube search returned no results")
                    
            except Exception as e:
                print(f"✗ yt-dlp extraction failed: {type(e).__name__}: {str(e)[:100]}")
                
    except ImportError:
        print("✗ yt-dlp not installed")

def main():
    print("\n" + "=" * 60)
    print("DISCORD MUSIC BOT DIAGNOSTIC TEST")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Working Directory: {os.getcwd()}")
    
    # Run tests
    ffmpeg_ok = test_ffmpeg()
    packages_ok = test_python_packages()
    test_network()
    
    if packages_ok:
        asyncio.run(test_discord_voice())
        test_youtube_extraction()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if ffmpeg_ok and packages_ok:
        print("✓ Basic requirements seem OK")
        print("\nIf the bot still doesn't work, check:")
        print("1. Bot has proper permissions in Discord (Connect, Speak)")
        print("2. Windows Firewall isn't blocking connections")
        print("3. The YouTube URLs aren't region-blocked")
        print("4. Try running as Administrator")
        print("5. Check the enhanced debug output from the new player.py")
    else:
        print("✗ Some requirements are missing - fix the issues above")

if __name__ == "__main__":
    main()