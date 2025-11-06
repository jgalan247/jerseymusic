"""
Graceful shutdown handlers for Jersey Events application.

These handlers ensure proper cleanup when the application receives
termination signals (SIGTERM, SIGINT) from the container orchestrator.
"""
import logging
import signal
import sys
from django.db import connections
from django.core.cache import cache

logger = logging.getLogger(__name__)


def close_database_connections():
    """
    Explicitly close all database connections.
    Django normally handles this, but explicit closure ensures
    no connections are left hanging during shutdown.
    """
    try:
        for conn in connections.all():
            if conn.connection is not None:
                logger.info(f"Closing database connection: {conn.alias}")
                conn.close()
        logger.info("All database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}", exc_info=True)


def clear_cache():
    """
    Clear the cache on shutdown to ensure no stale data persists.
    This is particularly important for distributed caches.
    """
    try:
        cache.clear()
        logger.info("Cache cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)


def log_shutdown():
    """
    Log the shutdown event for monitoring and debugging.
    """
    logger.info("="*60)
    logger.info("Jersey Events application shutting down gracefully")
    logger.info("="*60)


def graceful_shutdown(signum, frame):
    """
    Main graceful shutdown handler.
    Called when the application receives SIGTERM or SIGINT.

    Args:
        signum: The signal number received
        frame: The current stack frame
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")

    # Perform cleanup tasks
    log_shutdown()
    close_database_connections()
    clear_cache()

    logger.info("Graceful shutdown complete, exiting...")
    sys.exit(0)


def register_shutdown_handlers():
    """
    Register signal handlers for graceful shutdown.

    This should be called during Django app initialization.
    Note: In production with gunicorn, the master process handles
    SIGTERM to workers, so this mainly helps with:
    - Development server shutdown
    - Additional cleanup before worker exit
    - Logging shutdown events
    """
    try:
        # Register handlers for common termination signals
        signal.signal(signal.SIGTERM, graceful_shutdown)
        signal.signal(signal.SIGINT, graceful_shutdown)

        # Log successful registration
        logger.info("Shutdown handlers registered successfully")
        logger.debug("Registered handlers for: SIGTERM, SIGINT")
    except Exception as e:
        # Log error but don't prevent app startup
        logger.error(f"Failed to register shutdown handlers: {e}", exc_info=True)


# Optional: Register an atexit handler as a backup
import atexit

def atexit_cleanup():
    """
    Cleanup function called on normal Python exit.
    This is a backup to signal handlers.
    """
    logger.debug("atexit cleanup handler called")
    close_database_connections()

atexit.register(atexit_cleanup)
