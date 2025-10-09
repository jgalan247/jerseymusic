"""
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
            default='/Users/josegalan/Documents/jersey_music/ssl/localhost.crt',
            help='Path to SSL certificate file'
        )
        parser.add_argument(
            '--key', dest='key_path',
            default='/Users/josegalan/Documents/jersey_music/ssl/localhost.key',
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
                self.style.ERROR(f'Certificate file not found: {cert_path}')
            )
            return

        if not os.path.exists(key_path):
            self.stdout.write(
                self.style.ERROR(f'Key file not found: {key_path}')
            )
            return

        # Start HTTPS server
        self.stdout.write(
            self.style.SUCCESS(f'🔐 Starting HTTPS development server at https://{addr}:{port}/')
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
            self.stdout.write('\n🛑 HTTPS server stopped')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error starting HTTPS server: {e}')
            )
