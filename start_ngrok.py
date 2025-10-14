#!/usr/bin/env python3
"""
Script to start ngrok and automatically update configuration files with the new URL
"""
import subprocess
import time
import requests
import os
import re
from pathlib import Path

def start_ngrok(port=8000):
    """Start ngrok tunnel"""
    print(f"🚀 Starting ngrok on port {port}...")
    
    # Start ngrok in the background
    process = subprocess.Popen(
        ['ngrok', 'http', str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for ngrok to initialize (give it more time)
    print("⏳ Waiting for ngrok to initialize...")
    time.sleep(5)
    
    return process

def get_ngrok_url(max_retries=10):
    """Get the public ngrok URL from the local API"""
    print("🔍 Fetching ngrok URL...")
    
    for attempt in range(max_retries):
        try:
            response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
            data = response.json()
            
            # Get the HTTPS tunnel URL
            tunnels = data.get('tunnels', [])
            for tunnel in tunnels:
                if tunnel.get('proto') == 'https':
                    url = tunnel.get('public_url')
                    print(f"✅ Ngrok URL obtained: {url}")
                    return url
            
            # No HTTPS tunnel yet, wait and retry
            if attempt < max_retries - 1:
                print(f"⏳ Waiting for tunnel... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"⏳ Ngrok not ready yet... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                print("❌ Could not connect to ngrok API")
                return None
        except Exception as e:
            print(f"❌ Error getting ngrok URL: {e}")
            return None
    
    print("❌ No HTTPS tunnel found after all retries")
    return None

def update_env_file(ngrok_url):
    """Update .env file with new ngrok URL"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("⚠️  .env file not found, creating new one...")
        env_path.touch()
    
    # Read current content
    content = env_path.read_text() if env_path.exists() else ""
    
    # Update or add SUMUP_WEBHOOK_URL
    webhook_pattern = r'SUMUP_WEBHOOK_URL=.*'
    new_line = f'SUMUP_WEBHOOK_URL={ngrok_url}'
    
    if re.search(webhook_pattern, content):
        # Update existing line
        content = re.sub(webhook_pattern, new_line, content)
        print("✅ Updated SUMUP_WEBHOOK_URL in .env")
    else:
        # Add new line
        if content and not content.endswith('\n'):
            content += '\n'
        content += f'\n# Ngrok URL (auto-updated)\n{new_line}\n'
        print("✅ Added SUMUP_WEBHOOK_URL to .env")
    
    # Write back to file
    env_path.write_text(content)

def update_settings_file(ngrok_url):
    """Update settings.py if it contains hardcoded URLs"""
    settings_path = Path('settings.py')
    
    if not settings_path.exists():
        print("⚠️  settings.py not found, skipping...")
        return
    
    content = settings_path.read_text()
    
    # Check if there are any hardcoded ngrok URLs to replace
    ngrok_pattern = r'https://[a-z0-9-]+\.ngrok-free\.app'
    
    if re.search(ngrok_pattern, content):
        # Replace old ngrok URLs with new one
        content = re.sub(ngrok_pattern, ngrok_url, content)
        settings_path.write_text(content)
        print("✅ Updated ngrok URLs in settings.py")
    else:
        print("ℹ️  No hardcoded ngrok URLs found in settings.py")

def display_info(ngrok_url, port):
    """Display useful information"""
    print("\n" + "="*60)
    print("🎉 NGROK SUCCESSFULLY STARTED")
    print("="*60)
    print(f"\n📍 Public URL: {ngrok_url}")
    print(f"🔧 Local Server: http://localhost:{port}")
    print(f"📊 Ngrok Dashboard: http://localhost:4040")
    print("\n💡 Your .env file has been updated with the new URL")
    print("💡 Make sure your Django/Flask server is running on port", port)
    print("\n⚠️  Press Ctrl+C to stop ngrok")
    print("="*60 + "\n")

def main():
    # Configuration
    PORT = 8000  # Change this to match your Django/Flask port
    
    print("\n🎯 Jersey Music - Ngrok Starter")
    print("="*60)
    
    # Check if ngrok is installed
    try:
        subprocess.run(['ngrok', 'version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Ngrok is not installed or not in PATH")
        print("💡 Install: brew install ngrok")
        return
    
    # Start ngrok
    process = start_ngrok(PORT)
    
    # Get the public URL
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("\n❌ Failed to get ngrok URL.")
        print("💡 Troubleshooting:")
        print("   - Check if ngrok is authenticated: ngrok config check")
        print("   - Try running manually: ngrok http 8000")
        print("   - Check ngrok dashboard: http://localhost:4040")
        process.terminate()
        return
    
    # Update configuration files
    update_env_file(ngrok_url)
    update_settings_file(ngrok_url)
    
    # Display info
    display_info(ngrok_url, PORT)
    
    try:
        # Keep the script running
        process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping ngrok...")
        process.terminate()
        print("✅ Ngrok stopped successfully")

if __name__ == "__main__":
    main()
