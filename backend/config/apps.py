from django.apps import AppConfig


class ConfigAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'

    def ready(self):
        # Start APScheduler in the real Django process only. With runserver's
        # autoreloader, RUN_MAIN is set to 'true' in the child (serving) process
        # and is not set in the parent (reloader) process. In production there is
        # no autoreloader, so RUN_MAIN is not set and the scheduler starts here.
        import os
        run_main = os.environ.get('RUN_MAIN')
        if run_main is not None and run_main != 'true':
            return
        try:
            from publishing.scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            print(f'[Scheduler] Could not start: {e}')
