from django.apps import AppConfig


class ConfigAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'

    def ready(self):
        try:
            from publishing.scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            print(f'[Scheduler] Could not start: {e}')

        # NOTE: Telegram polling is handled exclusively by the APScheduler job
        # (poll_telegram in publishing/scheduler.py). Running both the library-based
        # bot (python-telegram-bot Application) and the scheduler's manual getUpdates
        # at the same time causes a race condition where they steal updates from each
        # other, so the library-based bot is disabled here.
