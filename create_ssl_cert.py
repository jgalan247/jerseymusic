#!/usr/bin/env python3
"""
Create a self-signed SSL certificate for local HTTPS development.
Required for SumUp payment widget testing on localhost.
"""

import os
import subprocess
import sys
from pathlib import Path

def create_ssl_certificate():
    """Create a self-signed SSL certificate for localhost development."""

    # Create ssl directory
    ssl_dir = Path(__file__).parent / 'ssl'
    ssl_dir.mkdir(exist_ok=True)

    cert_path = ssl_dir / 'localhost.crt'
    key_path = ssl_dir / 'localhost.key'

    print("🔐 Creating self-signed SSL certificate for localhost...")
    print(f"📁 SSL directory: {ssl_dir}")

    # OpenSSL command to create self-signed certificate
    openssl_cmd = [
        'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
        '-keyout', str(key_path),
        '-out', str(cert_path),
        '-days', '365',
        '-nodes',
        '-subj', '/C=JE/ST=Jersey/L=St Helier/O=Jersey Events/OU=Development/CN=localhost'
    ]

    try:
        # Check if OpenSSL is available
        subprocess.run(['openssl', 'version'], check=True, capture_output=True)

        # Create the certificate
        result = subprocess.run(openssl_cmd, check=True, capture_output=True, text=True)

        print("✅ SSL certificate created successfully!")
        print(f"📄 Certificate: {cert_path}")
        print(f"🔑 Private key: {key_path}")

        # Create Django management command to run HTTPS server
        create_https_management_command(cert_path, key_path)

        print("\n🚀 To start HTTPS development server:")
        print("   python manage.py runserver_https")
        print("   OR")
        print(f"   python manage.py runserver --cert {cert_path} --key {key_path}")

        print("\n⚠️  Browser Security Warning:")
        print("   Your browser will show a security warning for self-signed certificates.")
        print("   Click 'Advanced' → 'Proceed to localhost (unsafe)' to continue.")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ OpenSSL command failed: {e}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        return False

    except FileNotFoundError:
        print("❌ OpenSSL not found. Please install OpenSSL:")
        print("   macOS: brew install openssl")
        print("   Ubuntu/Debian: sudo apt-get install openssl")
        print("   Windows: Download from https://slproweb.com/products/Win32OpenSSL.html")
        return False

def create_https_management_command(cert_path, key_path):
    """Create a Django management command for HTTPS development server."""

    management_dir = Path(__file__).parent / 'events' / 'management'
    commands_dir = management_dir / 'commands'

    # Create directories
    management_dir.mkdir(exist_ok=True)
    commands_dir.mkdir(exist_ok=True)

    # Create __init__.py files
    (management_dir / '__init__.py').touch()
    (commands_dir / '__init__.py').touch()

    # Create runserver_https command
    command_content = f'''"""
Django management command to run HTTPS development server.
"""

from django.core.management.base import BaseCommand
from django.core.management.commands.runserver import Command as RunserverCommand
import ssl
import socket
from django.core.servers.basehttp import get_internal_wsgi_application
from django.core.servers.basehttp import WSGIServer
from wsgiref.simple_server import make_server
import sys


class HTTPSWSGIServer(WSGIServer):
    """WSGI server with HTTPS support."""

    def __init__(self, server_address, RequestHandlerClass, cert_path, key_path):
        super().__init__(server_address, RequestHandlerClass)

        # Wrap socket with SSL
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)

        self.socket = context.wrap_socket(self.socket, server_side=True)


class Command(BaseCommand):
    """Run Django development server with HTTPS support."""

    help = 'Run Django development server with HTTPS support for SumUp widget testing'

    def add_arguments(self, parser):
        parser.add_argument(
            'addrport', nargs='?', default='8000',
            help='Optional port number, or ipaddr:port'
        )
        parser.add_argument(
            '--cert', dest='cert_path',
            default='{cert_path}',
            help='Path to SSL certificate file'
        )
        parser.add_argument(
            '--key', dest='key_path',
            default='{key_path}',
            help='Path to SSL private key file'
        )

    def handle(self, *args, **options):
        addrport = options['addrport']
        cert_path = options['cert_path']
        key_path = options['key_path']

        # Parse address and port
        if ':' in addrport:
            addr, port = addrport.split(':')
        else:
            addr, port = '127.0.0.1', addrport

        port = int(port)

        # Check certificate files exist
        import os
        if not os.path.exists(cert_path):
            self.stdout.write(
                self.style.ERROR(f'Certificate file not found: {{cert_path}}')
            )
            return

        if not os.path.exists(key_path):
            self.stdout.write(
                self.style.ERROR(f'Key file not found: {{key_path}}')
            )
            return

        # Start HTTPS server
        self.stdout.write(
            self.style.SUCCESS(f'🔐 Starting HTTPS development server at https://{{addr}}:{{port}}/')
        )
        self.stdout.write(
            self.style.WARNING('⚠️  Using self-signed certificate - browser will show security warning')
        )
        self.stdout.write(
            self.style.WARNING('   Click "Advanced" → "Proceed to localhost (unsafe)" to continue')
        )

        try:
            # Get WSGI application
            wsgi_application = get_internal_wsgi_application()

            # Create HTTPS server
            httpd = HTTPSWSGIServer((addr, port), None, cert_path, key_path)
            httpd.set_app(wsgi_application)

            # Start serving
            httpd.serve_forever()

        except KeyboardInterrupt:
            self.stdout.write('\\n🛑 HTTPS server stopped')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error starting HTTPS server: {{e}}')
            )
'''

    command_file = commands_dir / 'runserver_https.py'
    command_file.write_text(command_content)

    print(f"✅ Created Django management command: {command_file}")

def create_https_instructions():
    """Create instructions file for HTTPS setup."""

    instructions = '''# HTTPS Development Setup for SumUp Widget

## Why HTTPS is Required

SumUp payment widgets require HTTPS connections for security. This means localhost:8000 (HTTP) won't work for testing payment widgets.

## SSL Certificate Created

A self-signed SSL certificate has been created in the `ssl/` directory:
- `ssl/localhost.crt` - SSL certificate
- `ssl/localhost.key` - Private key

## Starting HTTPS Development Server

### Option 1: Django Management Command
```bash
python manage.py runserver_https
```

### Option 2: Manual Command
```bash
python manage.py runserver --cert ssl/localhost.crt --key ssl/localhost.key
```

### Option 3: Using stunnel (Alternative)
```bash
# Install stunnel
brew install stunnel  # macOS
sudo apt-get install stunnel4  # Ubuntu

# Create stunnel config and run
```

## Browser Security Warning

When you first visit https://localhost:8000, your browser will show a security warning because the certificate is self-signed.

**To proceed:**
1. Click "Advanced" or "Show details"
2. Click "Proceed to localhost (unsafe)" or "Continue to this site"
3. The warning appears because browsers don't trust self-signed certificates
4. This is normal for development and won't affect SumUp widget functionality

## Testing SumUp Widget

Once HTTPS is working:

1. Visit: https://localhost:8000/payments/widget/test/
2. The SumUp widget should load without X-Frame-Options errors
3. Test payment flow with SumUp test card numbers

## SumUp Test Card Numbers

- **Successful payment:** 4000 0000 0000 0002
- **Declined payment:** 4000 0000 0000 0127
- **Insufficient funds:** 4000 0000 0000 0119

## Production Deployment

For production, use a proper SSL certificate from:
- Let's Encrypt (free)
- Cloudflare (free)
- Commercial certificate provider

## Troubleshooting

### OpenSSL not found
```bash
# macOS
brew install openssl

# Ubuntu/Debian
sudo apt-get install openssl

# Windows
# Download from https://slproweb.com/products/Win32OpenSSL.html
```

### Permission errors
```bash
# Make sure you have write permissions to the project directory
chmod +x create_ssl_cert.py
```

### Browser still shows HTTP
- Clear browser cache
- Check URL starts with `https://`
- Restart browser
'''

    instructions_file = Path(__file__).parent / 'HTTPS_SETUP.md'
    instructions_file.write_text(instructions)

    print(f"📋 Created setup instructions: {instructions_file}")

if __name__ == '__main__':
    print("🚀 Setting up HTTPS for SumUp widget development...")
    print("=" * 60)

    success = create_ssl_certificate()

    if success:
        create_https_instructions()
        print("\n✅ HTTPS setup complete!")
        print("\n🔗 Next steps:")
        print("1. Run: python manage.py runserver_https")
        print("2. Visit: https://localhost:8000")
        print("3. Accept the security warning in your browser")
        print("4. Test SumUp widget at: https://localhost:8000/payments/widget/test/")
    else:
        print("\n❌ HTTPS setup failed. Please check error messages above.")
        sys.exit(1)