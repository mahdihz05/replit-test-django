import os
import re
import fcntl
import logging
import requests as req_lib
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

# In-memory offset tracking for bot getUpdates (resets on restart, which is fine)
_offsets = {'telegram': 0, 'bale': 0}
_started = False
_lock_fd = None

VERIFY_PATTERN = re.compile(r'VRF-[A-Z0-9]{8}')

LOCK_FILE_PATH = '/tmp/mohtavayar_scheduler.lock'

# ─────────────────────────────────────────────
# Bot polling — Telegram
# ─────────────────────────────────────────────

def poll_telegram():
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        return
    try:
        # Long-poll Telegram for up to 5 seconds. When a new message arrives,
        # Telegram returns immediately; otherwise it waits ~5s, then we retry.
        # This avoids overlapping short-poll requests when network latency is high.
        long_poll_timeout = 5
        url = f'https://api.telegram.org/bot{token}/getUpdates'
        resp = req_lib.get(url, params={
            'offset': _offsets['telegram'],
            'timeout': long_poll_timeout,
            'allowed_updates': ['message', 'channel_post'],
        }, timeout=long_poll_timeout + 5)
        if not resp.ok:
            return
        data = resp.json()
        if not data.get('ok'):
            return
        for update in data.get('result', []):
            _offsets['telegram'] = update['update_id'] + 1
            # Telegram sends channel posts as 'channel_post', group messages as 'message'
            msg = update.get('message') or update.get('channel_post', {})
            if not msg:
                continue
            text = msg.get('text', '') or ''
            chat = msg.get('chat', {})
            match = VERIFY_PATTERN.search(text)
            if match:
                logger.info(
                    '[poll_telegram] Found verification code %s in chat %s (type: %s)',
                    match.group(), chat.get('id'), chat.get('type')
                )
                _process_code(
                    code=match.group(),
                    chat_id=str(chat.get('id', '')),
                    username=chat.get('username', '') or '',
                    chat_type=chat.get('type', 'channel'),
                    platform='telegram',
                    token=token,
                    message_id=msg.get('message_id'),
                )
    except Exception as e:
        logger.debug(f'[poll_telegram] {e}')


# ─────────────────────────────────────────────
# Bot polling — Bale
# ─────────────────────────────────────────────

def poll_bale():
    token = getattr(settings, 'BALE_BOT_TOKEN', None)
    if not token:
        return
    try:
        url = f'https://tapi.bale.ai/bot{token}/getUpdates'
        resp = req_lib.get(url, params={
            'offset': _offsets['bale'],
            'timeout': 0,
        }, timeout=8)
        if not resp.ok:
            return
        data = resp.json()
        if not data.get('ok'):
            return
        for update in data.get('result', []):
            _offsets['bale'] = update['update_id'] + 1
            msg = update.get('message', {})
            text = msg.get('text', '') or ''
            chat = msg.get('chat', {})
            match = VERIFY_PATTERN.search(text)
            if match:
                _process_code(
                    code=match.group(),
                    chat_id=str(chat.get('id', '')),
                    username=chat.get('username', '') or '',
                    chat_type=chat.get('type', 'channel'),
                    platform='bale',
                    token=token,
                    message_id=msg.get('message_id'),
                )
    except Exception as e:
        logger.debug(f'[poll_bale] {e}')


def _process_code(code, chat_id, username, chat_type, platform, token, message_id):
    """Match a VRF- code to a pending verification and activate the channel."""
    from channels_app.models import ChannelVerification, PublishChannel

    try:
        verification = ChannelVerification.objects.select_related('workspace').get(
            token=code,
            platform=platform,
            status='pending',
            expires_at__gt=timezone.now(),
        )
    except ChannelVerification.DoesNotExist:
        return

    # Map Telegram chat type → our channel_type
    ch_type = 'group' if chat_type in ('group', 'supergroup') else 'channel'

    # Create or get the channel record
    channel, created = PublishChannel.objects.get_or_create(
        workspace=verification.workspace,
        platform=platform,
        external_id=chat_id,
        defaults={
            'name': f'{platform.title()} {chat_id}',
            'username': username,
            'channel_type': ch_type,
            'is_verified': True,
            'is_active': True,
        },
    )
    if not created:
        channel.is_verified = True
        channel.username = username or channel.username
        channel.channel_type = ch_type
        channel.save()

    # Mark verification as complete
    verification.status = 'verified'
    verification.channel = channel
    verification.save()

    logger.info(f'[bot] Channel verified: {chat_id} on {platform}')

    # Try to delete the code message (bot must be admin)
    _api_call(platform, token, 'deleteMessage', {
        'chat_id': chat_id,
        'message_id': message_id,
    })

    # Send confirmation message
    _api_call(platform, token, 'sendMessage', {
        'chat_id': chat_id,
        'text': '✅ کانال با موفقیت به سامانه محتوایار متصل شد.',
    })


def _api_call(platform, token, method, payload):
    try:
        if platform == 'telegram':
            base = f'https://api.telegram.org/bot{token}'
        else:
            base = f'https://tapi.bale.ai/bot{token}'
        req_lib.post(f'{base}/{method}', json=payload, timeout=5)
    except Exception:
        pass


# ─────────────────────────────────────────────
# Publish queue processor
# ─────────────────────────────────────────────

def process_publish_queue():
    from .models import PublishJob, PublishLog

    now = timezone.now()
    jobs = (
        PublishJob.objects.filter(status='queued', scheduled_at__isnull=True) |
        PublishJob.objects.filter(status='queued', scheduled_at__lte=now)
    )

    for job in jobs.select_related('content', 'channel'):
        job.status = 'processing'
        job.started_at = now
        job.save()

        success, error_type, error_msg = attempt_publish(job)
        job.attempt_count += 1

        log = PublishLog(job=job, attempt_number=job.attempt_count, success=success)

        if success:
            job.status = 'success'
            job.completed_at = timezone.now()
            log.api_response = {}
        else:
            log.error_type = error_type or 'unknown'
            log.error_message = error_msg or ''
            log.user_message = PublishLog.USER_MESSAGES.get(
                error_type, PublishLog.USER_MESSAGES['unknown']
            )
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
    PublishJob.objects.filter(
        status='queued',
        next_retry_at__lte=timezone.now(),
    ).update(next_retry_at=None)


def expire_otp_codes():
    from users.models import OTPCode
    OTPCode.objects.filter(is_used=False, expires_at__lt=timezone.now()).update(is_used=True)


def expire_verifications():
    from channels_app.models import ChannelVerification
    ChannelVerification.objects.filter(
        status='pending',
        expires_at__lt=timezone.now(),
    ).update(status='expired')


# ─────────────────────────────────────────────
# Scheduler startup
# ─────────────────────────────────────────────

def _acquire_scheduler_lock():
    """Cross-process PID lock. Only one scheduler runs across all Django processes."""
    try:
        if os.path.exists(LOCK_FILE_PATH):
            try:
                with open(LOCK_FILE_PATH, 'r') as f:
                    old_pid = int(f.read().strip())
                # If the old process is still alive, we cannot take the lock.
                os.kill(old_pid, 0)
                return False
            except (ValueError, ProcessLookupError, FileNotFoundError):
                # Stale lock file or dead process — take over.
                pass
            except PermissionError:
                return False
        with open(LOCK_FILE_PATH, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return False


def start_scheduler():
    global _started
    if _started:
        return None
    if not _acquire_scheduler_lock():
        return None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler()

        # Bot polling via long-polling — every 5 seconds to avoid overlapping requests
        scheduler.add_job(poll_telegram, IntervalTrigger(seconds=5), id='poll_telegram',
                          max_instances=1, coalesce=True)
        scheduler.add_job(poll_bale, IntervalTrigger(seconds=5), id='poll_bale',
                          max_instances=1, coalesce=True)

        # Publish queue — every 60 seconds
        scheduler.add_job(process_publish_queue, IntervalTrigger(minutes=1), id='publish_queue',
                          max_instances=1, coalesce=True)
        scheduler.add_job(process_retries, IntervalTrigger(minutes=5), id='retries')
        scheduler.add_job(expire_otp_codes, IntervalTrigger(hours=1), id='expire_otp')
        scheduler.add_job(expire_verifications, IntervalTrigger(hours=1), id='expire_verifications')

        scheduler.start()
        _started = True
        logger.info('[Scheduler] Started in process %s — bot polling every 1s', os.getpid())
        return scheduler
    except Exception as e:
        logger.exception('[Scheduler] Failed to start')
        return None
