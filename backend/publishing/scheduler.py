from datetime import timedelta
from django.utils import timezone


def process_publish_queue():
    from .models import PublishJob, PublishLog
    import django
    django.setup()

    now = timezone.now()
    jobs = PublishJob.objects.filter(
        status='queued'
    ).filter(
        scheduled_at__isnull=True
    ) | PublishJob.objects.filter(
        status='queued',
        scheduled_at__lte=now
    )

    for job in jobs.select_related('content', 'channel'):
        job.status = 'processing'
        job.started_at = now
        job.save()

        success, error_type, error_msg = attempt_publish(job)
        job.attempt_count += 1

        log = PublishLog(
            job=job,
            attempt_number=job.attempt_count,
            success=success,
        )

        if success:
            job.status = 'success'
            job.completed_at = timezone.now()
            log.api_response = {}
        else:
            log.error_type = error_type or 'unknown'
            log.error_message = error_msg or ''
            log.user_message = PublishLog.USER_MESSAGES.get(error_type, PublishLog.USER_MESSAGES['unknown'])

            if job.attempt_count < job.max_attempts:
                job.status = 'queued'
                job.next_retry_at = timezone.now() + timedelta(minutes=5 * job.attempt_count)
            else:
                job.status = 'failed'

        log.save()
        job.save()

        update_content_status(job.content)


def attempt_publish(job):
    channel = job.channel
    content = job.content

    if channel.platform == 'telegram':
        from .publishers import telegram
        return telegram.publish(channel, content)
    elif channel.platform == 'bale':
        from .publishers import bale
        return bale.publish(channel, content)
    elif channel.platform == 'website':
        from .publishers import website
        return website.publish(channel, content)

    return False, 'unknown', 'Unknown platform'


def update_content_status(content):
    jobs = content.publish_jobs.all()
    if not jobs.exists():
        return
    if all(j.status == 'success' for j in jobs):
        content.status = 'published'
        content.published_at = timezone.now()
    elif any(j.status == 'failed' for j in jobs):
        content.status = 'failed'
    content.save()


def process_retries():
    from .models import PublishJob
    now = timezone.now()
    PublishJob.objects.filter(
        status='queued',
        next_retry_at__lte=now
    ).update(next_retry_at=None)


def expire_otp_codes():
    from users.models import OTPCode
    OTPCode.objects.filter(
        is_used=False,
        expires_at__lt=timezone.now()
    ).update(is_used=True)


def expire_verifications():
    from channels_app.models import ChannelVerification
    ChannelVerification.objects.filter(
        status='pending',
        expires_at__lt=timezone.now()
    ).update(status='expired')


def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler()
        scheduler.add_job(process_publish_queue, IntervalTrigger(minutes=1), id='publish_queue')
        scheduler.add_job(process_retries, IntervalTrigger(minutes=5), id='retries')
        scheduler.add_job(expire_otp_codes, IntervalTrigger(hours=1), id='expire_otp')
        scheduler.add_job(expire_verifications, IntervalTrigger(hours=1), id='expire_verifications')
        scheduler.start()
        print('[Scheduler] Started successfully')
        return scheduler
    except Exception as e:
        print(f'[Scheduler] Failed to start: {e}')
        return None
