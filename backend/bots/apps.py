from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class BotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bots'

    def ready(self):
        # Avoid starting the bot in the autoreloader parent process.
        import os
        run_main = os.environ.get('RUN_MAIN')
        if run_main is not None and run_main != 'true':
            return
        try:
            from .telegram_bot import start_bot
            start_bot()
        except Exception as e:
            logger.exception(f'[Bots] Could not start Telegram bot: {e}')

        try:
            from .bale_bot import start_bale_bot
            start_bale_bot()
        except Exception as e:
            logger.exception(f'[Bots] Could not start Bale bot: {e}')
