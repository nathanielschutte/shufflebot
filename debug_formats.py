#!/usr/bin/env python3
"""
Debug script to see what formats YouTube is offering
"""

import yt_dlp
import sys

def list_formats(query):
    """List all available formats for a YouTube video"""
    
    print(f"Checking formats for: '{query}'")
    print("-" * 80)
    
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Search for the video
            result = ydl.extract_info(f"ytsearch:{query}", download=False)
            
            if not result or 'entries' not in result:
                print("No results found")
                return
                
            entry = result['entries'][0]
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            
            print(f"Video: {entry.get('title', 'Unknown')}")
            print(f"URL: {video_url}")
            print("-" * 80)
            
            # Get full info with formats
            info = ydl.extract_info(video_url, download=False)
            
            formats = info.get('formats', [])
            print(f"Total formats available: {len(formats)}")
            print()
            
            # Separate audio-only and video+audio formats
            audio_only = []
            video_audio = []
            
            for f in formats:
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_only.append(f)
                elif f.get('acodec') != 'none':
                    video_audio.append(f)
            
            print(f"Audio-only formats: {len(audio_only)}")
            for f in audio_only[:5]:  # Show first 5
                format_id = str(f.get('format_id', 'N/A'))
                ext = str(f.get('ext', 'N/A'))
                acodec = str(f.get('acodec', 'N/A'))
                abr = str(f.get('abr', 'N/A'))
                filesize = str(f.get('filesize_approx', 'unknown'))
                print(f"  {format_id:>4} | {ext:>4} | {acodec:>10} @ {abr:>4}kbps | filesize: {filesize:>10}")
            
            print()
            print(f"Video+Audio formats: {len(video_audio)}")
            for f in video_audio[:5]:  # Show first 5
                format_id = str(f.get('format_id', 'N/A'))
                ext = str(f.get('ext', 'N/A'))
                vcodec = str(f.get('vcodec', 'N/A'))
                acodec = str(f.get('acodec', 'N/A'))
                abr = str(f.get('abr', 'N/A'))
                resolution = str(f.get('resolution', 'unknown'))
                print(f"  {format_id:>4} | {ext:>4} | {vcodec:>10}/{acodec:>10} @ {abr:>4}kbps | {resolution:>10}")
            
            # Test format selection
            print("\n" + "-" * 80)
            print("Testing format selectors:")
            
            test_formats = [
                'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
                'bestaudio/best',
                'best',
                None  # Let yt-dlp choose
            ]
            
            for fmt in test_formats:
                try:
                    test_opts = opts.copy()
                    if fmt:
                        test_opts['format'] = fmt
                    
                    with yt_dlp.YoutubeDL(test_opts) as test_ydl:
                        test_info = test_ydl.extract_info(video_url, download=False)
                        
                        if 'url' in test_info:
                            print(f"✓ Format '{fmt}': SUCCESS - Direct URL available")
                        elif 'requested_formats' in test_info:
                            print(f"✓ Format '{fmt}': SUCCESS - Requested formats available")
                        else:
                            print(f"✗ Format '{fmt}': No URL found")
                            
                except Exception as e:
                    print(f"✗ Format '{fmt}': ERROR - {str(e)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else "never gonna give you up"
    list_formats(query)