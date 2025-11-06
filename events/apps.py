"""
Django AppConfig for Events application.
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class EventsConfig(AppConfig):
    """
    Configuration for the Events application.

    This handles application initialization including registering
    graceful shutdown handlers for container orchestration.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'
    verbose_name = 'Jersey Events'

    def ready(self):
        """
        Called when Django starts up.

        Register shutdown handlers to ensure graceful termination
        when the container receives SIGTERM or SIGINT signals.
        """
        # Import here to avoid AppRegistryNotReady error
        from .shutdown_handlers import register_shutdown_handlers

        try:
            register_shutdown_handlers()
            logger.info(f"{self.verbose_name} app initialized with shutdown handlers")
        except Exception as e:
            # Log but don't crash on handler registration failure
            logger.error(f"Failed to initialize shutdown handlers: {e}", exc_info=True)
