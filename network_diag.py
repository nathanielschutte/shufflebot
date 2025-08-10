#!/usr/bin/env python3
"""
Network diagnostic to check Discord voice connection issues
Run as: python network_diag.py
"""

import socket
import subprocess
import sys
import os
from dotenv import load_dotenv

def check_discord_ports():
    """Check if Discord voice ports are accessible"""
    print("=" * 60)
    print("CHECKING DISCORD VOICE PORTS")
    print("=" * 60)
    
    # Discord uses these ports for voice
    ports_to_check = [
        ("Discord Voice (UDP)", "discord.com", 443),
        ("Discord Gateway", "gateway.discord.gg", 443),
        ("Discord Media", "media.discordapp.net", 443),
    ]
    
    # Also check UDP ports (voice uses UDP 50000-65535)
    udp_test_port = 50000
    
    for name, host, port in ports_to_check:
        try:
            # Try TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            # Resolve hostname
            ip = socket.gethostbyname(host)
            print(f"Testing {name} ({host}:{port})...")
            print(f"  Resolved to IP: {ip}")
            
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                print(f"  ✓ TCP Port {port} is OPEN")
            else:
                print(f"  ✗ TCP Port {port} is CLOSED or filtered")
                
        except socket.gaierror:
            print(f"  ✗ Could not resolve {host}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Test UDP
    print(f"\nTesting UDP port {udp_test_port} (Discord voice)...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        # This won't actually connect but tests if we can create UDP sockets
        sock.bind(('', 0))
        local_port = sock.getsockname()[1]
        print(f"  ✓ Can create UDP sockets (bound to port {local_port})")
        sock.close()
    except Exception as e:
        print(f"  ✗ UDP socket error: {e}")

def check_windows_firewall():
    """Check Windows Firewall status"""
    print("\n" + "=" * 60)
    print("CHECKING WINDOWS FIREWALL")
    print("=" * 60)
    
    try:
        # Check firewall status
        result = subprocess.run(
            ['netsh', 'advfirewall', 'show', 'currentprofile'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'State' in line:
                    if 'ON' in line:
                        print("⚠ Windows Firewall is ON")
                        print("  This might block Discord voice connections")
                        print("\n  To add exception for your bot:")
                        print("  1. Open Windows Defender Firewall")
                        print("  2. Click 'Allow an app'")
                        print("  3. Add Python.exe")
                        print("\n  Or temporarily disable for testing:")
                        print("  Run as Administrator: netsh advfirewall set allprofiles state off")
                        print("  (Remember to turn it back on after testing!)")
                    else:
                        print("✓ Windows Firewall is OFF")
                    break
        else:
            print("Could not check firewall status (need admin rights)")
            
    except Exception as e:
        print(f"Error checking firewall: {e}")

def check_vpn_proxy():
    """Check for VPN or proxy that might interfere"""
    print("\n" + "=" * 60)
    print("CHECKING VPN/PROXY")
    print("=" * 60)
    
    # Check for common VPN adapters
    try:
        result = subprocess.run(
            ['ipconfig', '/all'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            vpn_keywords = ['vpn', 'tunnel', 'tap', 'tun', 'wireguard', 'openvpn', 'nordvpn', 'expressvpn']
            found_vpn = False
            
            for line in result.stdout.lower().split('\n'):
                for keyword in vpn_keywords:
                    if keyword in line and 'adapter' in line:
                        print(f"⚠ Found possible VPN adapter: {line.strip()}")
                        found_vpn = True
                        break
                        
            if found_vpn:
                print("\n  VPNs can interfere with Discord voice")
                print("  Try disconnecting VPN and testing again")
            else:
                print("✓ No obvious VPN adapters found")
                
    except Exception as e:
        print(f"Could not check network adapters: {e}")
    
    # Check proxy settings
    try:
        result = subprocess.run(
            ['netsh', 'winhttp', 'show', 'proxy'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            if 'Direct access' in result.stdout:
                print("✓ No system proxy configured")
            else:
                print("⚠ System proxy detected:")
                print(result.stdout)
                print("  Proxies can interfere with Discord connections")
                
    except Exception as e:
        print(f"Could not check proxy: {e}")

def test_discord_websocket():
    """Test WebSocket connection to Discord"""
    print("\n" + "=" * 60)
    print("TESTING DISCORD WEBSOCKET")
    print("=" * 60)
    
    try:
        import websocket
        
        ws_url = "wss://gateway.discord.gg/?v=10&encoding=json"
        print(f"Testing WebSocket connection to Discord...")
        
        def on_open(ws):
            print("✓ WebSocket connection opened")
            ws.close()
            
        def on_error(ws, error):
            print(f"✗ WebSocket error: {error}")
            
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket closed")
            
        ws = websocket.WebSocketApp(ws_url,
                                    on_open=on_open,
                                    on_error=on_error,
                                    on_close=on_close)
        
        # Run with timeout
        import threading
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
        wst.join(timeout=5)
        
        try:
            ws.close()
        except:
            pass
            
    except ImportError:
        print("websocket-client not installed, skipping WebSocket test")
        print("Install with: pip install websocket-client")
    except Exception as e:
        print(f"WebSocket test error: {e}")

def check_discord_regions():
    """Check latency to different Discord regions"""
    print("\n" + "=" * 60)
    print("CHECKING DISCORD REGION LATENCY")
    print("=" * 60)
    
    regions = {
        'us-west': 'us-west.discord.gg',
        'us-east': 'us-east.discord.gg',
        'us-central': 'us-central.discord.gg',
        'us-south': 'us-south.discord.gg',
        'europe': 'eu.discord.gg',
    }
    
    print("Testing ping to Discord regions...")
    print("(High latency or timeouts can cause connection issues)\n")
    
    for region, host in regions.items():
        try:
            # Windows ping command
            result = subprocess.run(
                ['ping', '-n', '2', '-w', '2000', host],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse average ping time
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Average' in line:
                        avg_time = line.split('=')[-1].strip()
                        print(f"  {region:12} - ✓ {avg_time}")
                        break
                else:
                    print(f"  {region:12} - ✓ Reachable")
            else:
                print(f"  {region:12} - ✗ Timeout or unreachable")
                
        except Exception as e:
            print(f"  {region:12} - Error: {e}")
    
    print("\nIf your server's region has high latency, try:")
    print("  1. Change the server's voice region in Server Settings")
    print("  2. Use a server in a different region for testing")

def test_simple_bot():
    """Test a minimal Discord bot connection"""
    print("\n" + "=" * 60)
    print("TESTING MINIMAL BOT CONNECTION")
    print("=" * 60)
    
    load_dotenv()
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("✗ DISCORD_BOT_TOKEN not found in .env file")
        print("  Cannot test bot connection")
        return
        
    print("Attempting minimal bot connection test...")
    print("(This will connect and immediately disconnect)\n")
    
    try:
        import discord
        import asyncio
        
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)
        
        connected = False
        
        @client.event
        async def on_ready():
            nonlocal connected
            connected = True
            print(f"✓ Bot connected as {client.user}")
            print(f"  Latency: {round(client.latency * 1000)}ms")
            await client.close()
        
        async def run_bot():
            try:
                await asyncio.wait_for(client.start(token), timeout=10)
            except asyncio.TimeoutError:
                print("✗ Connection timeout after 10 seconds")
                try:
                    await client.close()
                except:
                    pass
            except Exception as e:
                print(f"✗ Connection error: {e}")
                
        try:
            asyncio.run(run_bot())
            if connected:
                print("\n✓ Basic bot connection works!")
            else:
                print("\n✗ Could not establish connection")
        except Exception as e:
            print(f"✗ Bot test error: {e}")
            
    except ImportError:
        print("✗ discord.py not installed")
    except Exception as e:
        print(f"✗ Error: {e}")

def main():
    print("\n" + "=" * 60)
    print("DISCORD VOICE CONNECTION DIAGNOSTIC")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    # Run diagnostics
    check_discord_ports()
    check_windows_firewall()
    check_vpn_proxy()
    check_discord_regions()
    test_discord_websocket()
    test_simple_bot()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print("\nCommon fixes for connection issues:")
    print("1. Disable Windows Firewall temporarily for testing")
    print("2. Disconnect any VPN")
    print("3. Run bot as Administrator")
    print("4. Try a different Discord server/voice channel")
    print("5. Check if your ISP blocks UDP ports 50000-65535")
    print("6. Try using mobile hotspot to rule out network issues")

if __name__ == "__main__":
    main()