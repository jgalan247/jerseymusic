#!/usr/bin/env python3
"""
Automated ngrok setup for Jersey Events
Starts ngrok, gets URL, updates configuration automatically
"""

import subprocess
import time
import requests
import json
import re
import os
import sys
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

def check_ngrok_installed():
    """Check if ngrok is installed"""
    try:
        subprocess.run(['ngrok', 'version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_ngrok():
    """Start ngrok tunnel"""
    print_info("Starting ngrok tunnel on port 8000...")
    
    # Kill any existing ngrok processes
    try:
        subprocess.run(['pkill', '-f', 'ngrok'], capture_output=True)
        time.sleep(1)
    except:
        pass
    
    # Start ngrok in background
    process = subprocess.Popen(
        ['ngrok', 'http', '8000'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for ngrok to start
    time.sleep(3)
    
    return process

def get_ngrok_url():
    """Get public URL from ngrok API"""
    try:
        response = requests.get('http://127.0.0.1:4040/api/tunnels')
        data = response.json()
        
        # Get the HTTPS URL
        for tunnel in data['tunnels']:
            if tunnel['proto'] == 'https':
                return tunnel['public_url']
        
        # Fallback to first tunnel
        if data['tunnels']:
            return data['tunnels'][0]['public_url']
            
    except Exception as e:
        print_error(f"Could not get ngrok URL: {e}")
        return None

def update_env_file(ngrok_url):
    """Update .env file with new ngrok URL"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print_error(".env file not found!")
        return False
    
    print_info("Updating .env file...")

    # Read current .env
    with open(env_path, 'r') as f:
        content = f.read()

    # Update SUMUP_REDIRECT_URI
    # FIXED: Use correct OAuth callback URL (accounts app, not payments)
    redirect_uri = f"{ngrok_url}/accounts/sumup/callback/"
    
    # Pattern to match SUMUP_REDIRECT_URI line
    pattern = r'SUMUP_REDIRECT_URI=.*'
    replacement = f'SUMUP_REDIRECT_URI={redirect_uri}'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
    else:
        # Add if not exists
        content += f'\nSUMUP_REDIRECT_URI={redirect_uri}\n'
    
    # Also update other URLs if they exist
    urls_to_update = {
        'SUMUP_RETURN_URL': f'{ngrok_url}/payments/sumup/success/',
        'SUMUP_FAIL_URL': f'{ngrok_url}/payments/fail/',
        'SUMUP_CANCEL_URL': f'{ngrok_url}/payments/cancel/',
        'SUMUP_WEBHOOK_URL': f'{ngrok_url}/payments/sumup/webhook/',
    }
    
    for key, value in urls_to_update.items():
        pattern = f'{key}=.*'
        replacement = f'{key}={value}'
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
    
    # Write updated .env
    with open(env_path, 'w') as f:
        f.write(content)
    
    print_success("Updated .env file")
    return True

def update_settings_file(ngrok_url):
    """Update settings.py with ngrok URL"""
    settings_path = Path('events/settings.py')
    
    if not settings_path.exists():
        print_warning("settings.py not found at events/settings.py")
        return False
    
    print_info("Updating settings.py...")
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    # Extract hostname from ngrok URL
    hostname = ngrok_url.replace('https://', '').replace('http://', '')
    
    # Update ALLOWED_HOSTS
    allowed_hosts_pattern = r"ALLOWED_HOSTS\s*=\s*\[([^\]]*)\]"
    match = re.search(allowed_hosts_pattern, content)
    
    if match:
        current_hosts = match.group(1)
        if hostname not in current_hosts:
            # Add ngrok hostname to existing list
            new_hosts = f"{current_hosts.rstrip()}, '{hostname}']"
            content = content.replace(match.group(0), f"ALLOWED_HOSTS = [{new_hosts}")
    else:
        # ALLOWED_HOSTS not found, add it
        allowed_hosts_line = f"\nALLOWED_HOSTS = ['localhost', '127.0.0.1', '{hostname}']\n"
        # Add after DEBUG setting
        debug_pattern = r"(DEBUG\s*=\s*.*\n)"
        content = re.sub(debug_pattern, r"\1" + allowed_hosts_line, content)
    
    # Update or add CSRF_TRUSTED_ORIGINS
    csrf_pattern = r"CSRF_TRUSTED_ORIGINS\s*=\s*\[([^\]]*)\]"
    csrf_match = re.search(csrf_pattern, content)
    
    csrf_origins = f"https://{hostname}"
    
    if csrf_match:
        current_origins = csrf_match.group(1)
        if hostname not in current_origins:
            new_origins = f"{current_origins.rstrip()}, '{csrf_origins}']"
            content = content.replace(csrf_match.group(0), f"CSRF_TRUSTED_ORIGINS = [{new_origins}")
    else:
        # Add CSRF_TRUSTED_ORIGINS
        csrf_line = f"\nCSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000', '{csrf_origins}']\n"
        # Add after ALLOWED_HOSTS
        content = re.sub(r"(ALLOWED_HOSTS\s*=\s*\[([^\]]*)\]\s*\n)", r"\1" + csrf_line, content)
    
    # Write updated settings
    with open(settings_path, 'w') as f:
        f.write(content)
    
    print_success("Updated settings.py")
    return True

def create_ngrok_info_file(ngrok_url):
    """Create a file with ngrok URLs for reference"""
    info = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    NGROK CONFIGURATION                           ║
╚══════════════════════════════════════════════════════════════════╝

🌐 Your ngrok URL: {ngrok_url}

📝 URLs TO ADD TO SUMUP DASHBOARD:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Go to: https://developer.sumup.com/
2. Login and select your application
3. Find "Redirect URIs" section
4. Add these URLs:

   ✓ {ngrok_url}/payments/sumup/oauth/callback/
   ✓ http://localhost:8000/payments/sumup/oauth/callback/

5. Save changes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 ACCESS YOUR APP:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Dashboard: {ngrok_url}/accounts/organiser-dashboard/
   Admin:     {ngrok_url}/admin/
   Home:      {ngrok_url}/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  IMPORTANT:
    • ngrok URL changes every restart (free plan)
    • Run this script again if you restart ngrok
    • Django server is running on http://localhost:8000

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    with open('NGROK_INFO.txt', 'w') as f:
        f.write(info)
    
    print(info)

def main():
    print_header("JERSEY EVENTS - NGROK AUTO SETUP")
    
    # Check if ngrok is installed
    if not check_ngrok_installed():
        print_error("ngrok is not installed!")
        print_info("Install with: brew install ngrok (macOS)")
        print_info("Or download from: https://ngrok.com/download")
        sys.exit(1)
    
    print_success("ngrok is installed")
    
    # Start ngrok
    ngrok_process = start_ngrok()
    print_success("ngrok started")
    
    # Get public URL
    print_info("Waiting for ngrok URL...")
    time.sleep(2)
    
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print_error("Could not get ngrok URL!")
        print_info("Make sure ngrok is running: ngrok http 8000")
        sys.exit(1)
    
    print_success(f"Got ngrok URL: {ngrok_url}")
    
    # Update configuration files
    update_env_file(ngrok_url)
    update_settings_file(ngrok_url)
    
    # Create info file
    create_ngrok_info_file(ngrok_url)
    
    print_header("SETUP COMPLETE!")
    
    print_info("Next steps:")
    print("1. Update SumUp dashboard with redirect URIs (see NGROK_INFO.txt)")
    print("2. Start Django: python manage.py runserver")
    print(f"3. Access your app: {ngrok_url}")
    
    print(f"\n{Colors.YELLOW}Press Ctrl+C to stop ngrok{Colors.END}")
    
    # Keep script running so ngrok stays alive
    try:
        ngrok_process.wait()
    except KeyboardInterrupt:
        print_info("\nStopping ngrok...")
        ngrok_process.terminate()
        print_success("ngrok stopped")

if __name__ == '__main__':
    main()
