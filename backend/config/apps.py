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

        import os
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from bots.telegram_bot import start_bot
                start_bot()
            except Exception as e:
                print(f'[Bot] Could not start: {e}')
