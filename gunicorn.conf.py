"""
Gunicorn configuration file for Jersey Events production deployment.

This configuration ensures graceful shutdown handling when the container
receives termination signals (SIGTERM, SIGINT).
"""
import multiprocessing
import os
import sys
import signal

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests (prevents memory leaks)
max_requests_jitter = 50  # Add randomness to max_requests to avoid all workers restarting simultaneously

# Timeouts
timeout = 30  # Worker timeout for processing a single request
graceful_timeout = 30  # Time to wait for workers to finish after receiving shutdown signal
keepalive = 2  # Keep-alive connections

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'jerseymusic'

# Server mechanics
daemon = False  # Don't daemonize (required for container orchestration)
pidfile = None  # Don't use pidfile in containers
umask = 0
user = None
group = None
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190


# Graceful shutdown handling
def on_starting(server):
    """
    Called just before the master process is initialized.
    """
    server.log.info("Starting gunicorn master process...")


def when_ready(server):
    """
    Called just after the server is started.
    """
    server.log.info(f"Gunicorn is ready. Listening on {bind} with {workers} workers")


def on_exit(server):
    """
    Called just before exiting gunicorn.
    """
    server.log.info("Gunicorn master process is exiting...")


def worker_int(worker):
    """
    Called when a worker receives the SIGINT or SIGQUIT signal.
    This is called in the worker process.
    """
    worker.log.info(f"Worker {worker.pid} received SIGINT/SIGQUIT, gracefully shutting down...")


def worker_abort(worker):
    """
    Called when a worker receives the SIGABRT signal.
    This call generally happens on timeout.
    """
    worker.log.warning(f"Worker {worker.pid} was aborted (timeout or crash)")


def pre_fork(server, worker):
    """
    Called just before a worker is forked.
    """
    pass


def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    """
    worker.log.info(f"Worker {worker.pid} spawned")


def pre_exec(server):
    """
    Called just before a new master process is forked.
    """
    server.log.info("Forking new master process...")


def worker_exit(server, worker):
    """
    Called just after a worker has been exited, in the master process.
    """
    server.log.info(f"Worker {worker.pid} exited")


# Handle signals for graceful shutdown
def handle_sigterm(signum, frame):
    """
    Handle SIGTERM for graceful shutdown.
    This is mainly for documentation - gunicorn already handles SIGTERM gracefully.
    """
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)
