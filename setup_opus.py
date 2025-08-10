#!/usr/bin/env python3
"""
Setup script to download and install the Opus library for Discord voice on Windows
Run this as: python setup_opus.py
"""

import os
import sys
import urllib.request
import shutil
import discord

def download_opus():
    """Download and install the opus library"""
    
    print("=" * 60)
    print("OPUS LIBRARY SETUP FOR DISCORD VOICE")
    print("=" * 60)
    
    # Check if already loaded
    if discord.opus.is_loaded():
        print("✓ Opus is already loaded and working!")
        return True
    
    print("Opus library not found. Setting it up...")
    
    # URLs for opus library
    opus_urls = {
        'x64': 'https://github.com/discord-net/Discord.Net/raw/dev/voice-natives/libopus-x64.dll',
        'x86': 'https://github.com/discord-net/Discord.Net/raw/dev/voice-natives/libopus-x86.dll'
    }
    
    # Determine architecture
    import platform
    is_64bit = platform.machine().endswith('64')
    arch = 'x64' if is_64bit else 'x86'
    url = opus_urls[arch]
    
    print(f"System architecture: {arch}")
    print(f"Download URL: {url}")
    
    # Try different installation locations
    install_locations = [
        # Current directory (always works)
        ('opus.dll', 'Current directory'),
        # Bot directory
        (os.path.join(os.getcwd(), 'opus.dll'), 'Bot directory'),
    ]
    
    # Add system directory if running as admin
    if os.name == 'nt':
        system32 = os.path.join(os.environ['SystemRoot'], 'System32')
        if is_64bit:
            install_locations.append((os.path.join(system32, 'opus.dll'), 'System32 (requires admin)'))
    
    # Download the file
    print(f"\nDownloading opus library from GitHub...")
    try:
        with urllib.request.urlopen(url) as response:
            opus_data = response.read()
            print(f"✓ Downloaded {len(opus_data)} bytes")
    except Exception as e:
        print(f"✗ Failed to download: {e}")
        print("\nManual download instructions:")
        print(f"1. Download from: {url}")
        print("2. Save as 'opus.dll' in your bot directory")
        return False
    
    # Try to save to different locations
    saved = False
    saved_path = None
    
    for path, description in install_locations:
        try:
            print(f"\nTrying to save to {description}: {path}")
            
            # Create backup if file exists
            if os.path.exists(path):
                backup = path + '.backup'
                shutil.copy2(path, backup)
                print(f"  Created backup: {backup}")
            
            # Write the file
            with open(path, 'wb') as f:
                f.write(opus_data)
            
            print(f"  ✓ Saved successfully")
            saved = True
            saved_path = path
            
            # Test if it loads
            try:
                discord.opus.load_opus(path)
                if discord.opus.is_loaded():
                    print(f"  ✓ Opus loaded successfully from {path}")
                    break
            except Exception as e:
                print(f"  ⚠ Could not load from this location: {e}")
                
        except PermissionError:
            print(f"  ✗ Permission denied (need admin rights)")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    if not saved:
        print("\n✗ Could not save opus.dll to any location")
        print("Please run this script as Administrator or manually place opus.dll in your bot directory")
        return False
    
    # Final test
    print("\n" + "=" * 60)
    print("TESTING OPUS LIBRARY")
    print("=" * 60)
    
    # Try to load with different names
    test_names = ['opus', 'opus.dll', saved_path] if saved_path else ['opus', 'opus.dll']
    
    for name in test_names:
        try:
            if not discord.opus.is_loaded():
                discord.opus.load_opus(name)
            
            if discord.opus.is_loaded():
                print(f"✓✓✓ SUCCESS! Opus is now loaded from: {name}")
                print("\nYour bot should now be able to play audio!")
                return True
        except:
            continue
    
    print("⚠ Opus was downloaded but couldn't be loaded")
    print(f"The file was saved to: {saved_path}")
    print("Try restarting your bot or Python")
    
    return False

def test_voice_setup():
    """Test if everything is set up correctly"""
    print("\n" + "=" * 60)
    print("TESTING COMPLETE VOICE SETUP")
    print("=" * 60)
    
    issues = []
    
    # Test opus
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus('opus')
        except:
            pass
    
    if discord.opus.is_loaded():
        print("✓ Opus library: READY")
    else:
        print("✗ Opus library: NOT LOADED")
        issues.append("Opus library not loaded")
    
    # Test FFmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✓ FFmpeg: READY")
        else:
            print("✗ FFmpeg: ERROR")
            issues.append("FFmpeg not working properly")
    except FileNotFoundError:
        print("✗ FFmpeg: NOT FOUND")
        issues.append("FFmpeg not installed or not in PATH")
    except:
        print("✗ FFmpeg: ERROR")
        issues.append("FFmpeg error")
    
    # Test discord.py
    try:
        print(f"✓ Discord.py: {discord.__version__}")
    except:
        print("✗ Discord.py: NOT INSTALLED")
        issues.append("Discord.py not installed")
    
    print("\n" + "=" * 60)
    if not issues:
        print("✓✓✓ ALL SYSTEMS GO! Your bot should work now!")
        print("\nRestart your bot with:")
        print("  python bot.py")
    else:
        print("✗ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nFix these issues and run this script again")

def main():
    print("\nDiscord Voice Setup for Windows")
    print("This will download and install the Opus library\n")
    
    if not download_opus():
        print("\n✗ Setup failed")
        sys.exit(1)
    
    test_voice_setup()
    
    print("\n" + "=" * 60)
    print("Setup complete! Restart your bot to use voice.")
    print("=" * 60)

if __name__ == "__main__":
    main()