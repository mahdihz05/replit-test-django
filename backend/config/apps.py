from django.apps import AppConfig


class ConfigAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'

    def ready(self):
        # Only run background workers in the main Django process, not in the
        # autoreloader parent process. This prevents duplicate APScheduler instances
        # during development (runserver with autoreload).
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            from publishing.scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            print(f'[Scheduler] Could not start: {e}')
