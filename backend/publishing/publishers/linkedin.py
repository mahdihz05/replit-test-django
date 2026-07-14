import requests
import logging
import time
import os
import mimetypes
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from channels_app.models import LinkedInConnection
from channels_app.crypto import decrypt_token

logger = logging.getLogger(__name__)

RESTLI_VERSION = '2.0.0'
MAX_COMMENTARY_LENGTH = 3000
LINKEDIN_DOCUMENT_EXTENSIONS = {'.pdf', '.ppt', '.pptx', '.doc', '.docx'}


def _headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'LinkedIn-Version': getattr(settings, 'LINKEDIN_API_VERSION', '202604'),
        'X-Restli-Protocol-Version': RESTLI_VERSION,
        'Content-Type': 'application/json',
    }


def _get_active_connection(channel):
    """Return the active LinkedIn connection bound to this channel."""
    conn_id = (channel.extra_data or {}).get('connection_id')
    if conn_id:
        try:
            return LinkedInConnection.objects.get(
                id=conn_id,
                workspace=channel.workspace,
                is_active=True,
                status='active',
            )
        except LinkedInConnection.DoesNotExist:
            pass
    # Fallback to the workspace+target lookup for backwards compatibility.
    try:
        return LinkedInConnection.objects.get(
            workspace=channel.workspace,
            platform_target=channel.channel_type or 'personal',
            is_active=True,
            status='active',
        )
    except (LinkedInConnection.DoesNotExist, LinkedInConnection.MultipleObjectsReturned):
        return None


def _register_upload(access_token, owner_urn):
    """Step 1: Register an image upload and get uploadUrl + asset URN."""
    url = 'https://api.linkedin.com/rest/images?action=initializeUpload'
    payload = {
        'initializeUploadRequest': {
            'owner': owner_urn,
        }
    }
    try:
        resp = requests.post(url, headers=_headers(access_token), json=payload, timeout=20)
        data = resp.json()
        if not resp.ok:
            logger.warning('LinkedIn image initialization failed (status=%s)', resp.status_code)
            return None, 'LinkedIn تصویر را برای بارگذاری نپذیرفت.'
        value = data.get('value', {})
        return {
            'upload_url': value.get('uploadUrl'),
            'asset_urn': value.get('image'),
        }, None
    except requests.exceptions.RequestException:
        logger.exception('LinkedIn image initialization request failed')
        return None, 'ارتباط با LinkedIn برای بارگذاری تصویر برقرار نشد.'


def _resolve_media_path_or_url(path_or_url):
    if not path_or_url:
        return None
    # Publisher attachments are server-owned files. Refusing remote URLs avoids
    # turning this worker into an SSRF/download proxy.
    if path_or_url.startswith(('http://', 'https://')):
        return None
    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = Path(path_or_url)
    if not candidate.is_absolute():
        candidate = media_root / path_or_url.lstrip('/\\')
    candidate = candidate.resolve()
    try:
        candidate.relative_to(media_root)
    except ValueError:
        return None
    return str(candidate) if candidate.is_file() else None


def _upload_binary(upload_url, image_path_or_url):
    """Step 2: Upload binary image data to the uploadUrl."""
    try:
        with open(image_path_or_url, 'rb') as f:
            image_data = f.read()
        content_type = mimetypes.guess_type(image_path_or_url)[0] or 'application/octet-stream'

        resp = requests.put(upload_url, data=image_data, headers={
            'Content-Type': content_type,
        }, timeout=30)
        if not resp.ok:
            return False, f'آپلود تصویر شکست خورد: {resp.status_code}'
        return True, None
    except Exception:
        logger.exception('LinkedIn binary upload failed')
        return False, 'بارگذاری فایل در LinkedIn ناموفق بود.'


def _register_upload_video(access_token, owner_urn, file_size):
    """Initialize the current multipart Videos API flow."""
    url = 'https://api.linkedin.com/rest/videos?action=initializeUpload'
    payload = {'initializeUploadRequest': {
        'owner': owner_urn,
        'fileSizeBytes': file_size,
        'uploadCaptions': False,
        'uploadThumbnail': False,
    }}
    try:
        resp = requests.post(url, headers=_headers(access_token), json=payload, timeout=20)
        data = resp.json()
        if not resp.ok:
            logger.warning('LinkedIn video initialization failed (status=%s)', resp.status_code)
            return None, 'LinkedIn ویدیو را برای بارگذاری نپذیرفت.'
        value = data.get('value', {})
        return {
            'upload_instructions': value.get('uploadInstructions', []),
            'upload_token': value.get('uploadToken', ''),
            'asset_urn': value.get('video'),
        }, None
    except requests.exceptions.RequestException:
        logger.exception('LinkedIn video initialization request failed')
        return None, 'ارتباط با LinkedIn برای بارگذاری ویدیو برقرار نشد.'


def _upload_video(access_token, owner_urn, file_path):
    file_size = os.path.getsize(file_path)
    if file_size < 75 * 1024 or file_size > 500 * 1024 * 1024:
        return None, 'حجم ویدیو LinkedIn باید بین ۷۵ کیلوبایت و ۵۰۰ مگابایت باشد.'
    meta, err = _register_upload_video(access_token, owner_urn, file_size)
    if err:
        return None, err
    instructions = meta.get('upload_instructions') or []
    if not instructions or not meta.get('asset_urn'):
        return None, 'پاسخ بارگذاری ویدیو از LinkedIn ناقص بود.'

    part_ids = []
    try:
        with open(file_path, 'rb') as source:
            for instruction in instructions:
                first = int(instruction['firstByte'])
                last = min(int(instruction['lastByte']), file_size - 1)
                source.seek(first)
                chunk = source.read(last - first + 1)
                response = requests.put(
                    instruction['uploadUrl'], data=chunk,
                    headers={'Content-Type': 'application/octet-stream'}, timeout=90,
                )
                etag = response.headers.get('ETag') or response.headers.get('etag')
                if not response.ok or not etag:
                    return None, 'بارگذاری یکی از بخش‌های ویدیو در LinkedIn ناموفق بود.'
                part_ids.append(etag.strip('"'))

        finalize = requests.post(
            'https://api.linkedin.com/rest/videos?action=finalizeUpload',
            headers=_headers(access_token),
            json={'finalizeUploadRequest': {
                'video': meta['asset_urn'],
                'uploadToken': meta.get('upload_token', ''),
                'uploadedPartIds': part_ids,
            }},
            timeout=30,
        )
        if not finalize.ok:
            logger.warning('LinkedIn video finalization failed (status=%s)', finalize.status_code)
            return None, 'نهایی‌سازی ویدیو در LinkedIn ناموفق بود.'
        return meta['asset_urn'], None
    except (OSError, requests.exceptions.RequestException):
        logger.exception('LinkedIn multipart video upload failed')
        return None, 'بارگذاری ویدیو در LinkedIn با خطا مواجه شد.'


def _register_document(access_token, owner_urn):
    response = requests.post(
        'https://api.linkedin.com/rest/documents?action=initializeUpload',
        headers=_headers(access_token),
        json={'initializeUploadRequest': {'owner': owner_urn}},
        timeout=20,
    )
    if not response.ok:
        logger.warning('LinkedIn document initialization failed (status=%s)', response.status_code)
        return None, 'LinkedIn سند را برای بارگذاری نپذیرفت.'
    value = response.json().get('value', {})
    return {'upload_url': value.get('uploadUrl'), 'asset_urn': value.get('document')}, None


def _upload_asset_for_channel(access_token, owner_urn, file_path, media_type):
    """Upload an image or video asset and return the URN."""
    if not file_path:
        return None, None
    if media_type == 'video':
        if Path(file_path).suffix.lower() != '.mp4':
            return None, 'LinkedIn در این مسیر فقط ویدیوی MP4 را می‌پذیرد.'
        return _upload_video(access_token, owner_urn, file_path)
    if media_type == 'document':
        if Path(file_path).suffix.lower() not in LINKEDIN_DOCUMENT_EXTENSIONS:
            return None, 'فرمت سند باید PDF، PPT، PPTX، DOC یا DOCX باشد.'
        if os.path.getsize(file_path) > 100 * 1024 * 1024:
            return None, 'حجم سند LinkedIn نباید بیشتر از ۱۰۰ مگابایت باشد.'
        meta, err = _register_document(access_token, owner_urn)
    else:
        try:
            with Image.open(file_path) as image:
                width, height = image.size
                image.verify()
            if width * height > 36_152_320:
                return None, 'ابعاد تصویر از محدودیت LinkedIn بیشتر است.'
        except (UnidentifiedImageError, OSError):
            return None, 'فایل تصویر معتبر نیست.'
        meta, err = _register_upload(access_token, owner_urn)
    if err:
        return None, err

    ok, err = _upload_binary(meta['upload_url'], file_path)
    if not ok:
        return None, err

    return meta['asset_urn'], None


def _classify_error(err_text, status_code):
    err_lower = (err_text or '').lower()
    if status_code == 401 or 'unauthorized' in err_lower or 'invalid access token' in err_lower:
        return 'auth_error', 'اعتبار اتصال LinkedIn منقضی شده است. لطفاً دوباره متصل شوید.'
    if status_code == 429 or 'throttle' in err_lower or 'rate limit' in err_lower:
        return 'rate_limit', 'به محدودیت روزانه انتشار LinkedIn رسیده‌اید؛ ارسال به فردا موکول شد.'
    if status_code >= 500 or 'connection' in err_lower or 'timeout' in err_lower:
        return 'connection_error', 'خطا در اتصال به LinkedIn. لطفاً دوباره تلاش کنید.'
    return 'unknown', 'LinkedIn درخواست انتشار را نپذیرفت. تنظیمات دسترسی و محتوای پست را بررسی کنید.'


def publish(channel, content, attachments=None):
    conn = _get_active_connection(channel)
    if not conn:
        return False, 'auth_error', 'اتصال LinkedIn فعال یافت نشد. لطفاً ابتدا متصل شوید.'

    if conn.access_token_expires_at and conn.access_token_expires_at <= timezone.now() + timedelta(minutes=5):
        if not refresh_token_if_needed(conn):
            conn.status = 'needs_reauth'
            conn.save(update_fields=['status'])
            return False, 'auth_error', 'اعتبار اتصال LinkedIn منقضی شده است. لطفاً دوباره متصل شوید.'

    access_token = decrypt_token(conn.access_token)
    if not access_token:
        return False, 'auth_error', 'اعتبار اتصال LinkedIn قابل خواندن نیست. لطفاً دوباره متصل شوید.'

    if conn.platform_target == 'organization':
        if not getattr(settings, 'LINKEDIN_ORG_ENABLED', False):
            return False, 'unknown', 'انتشار روی صفحه سازمانی LinkedIn فعلاً غیرفعال است.'
        author_urn = conn.organization_urn or channel.external_id
    else:
        author_urn = conn.person_urn or channel.external_id

    if not author_urn:
        return False, 'auth_error', 'URN پروفایل LinkedIn یافت نشد.'

    commentary = content.body or ''
    if content.title and content.title not in ('untitled', ''):
        commentary = f'{content.title}\n\n{commentary}'
    commentary = commentary.strip()
    if not commentary:
        return False, 'validation_error', 'متن پست LinkedIn نمی‌تواند خالی باشد.'
    if len(commentary) > MAX_COMMENTARY_LENGTH:
        return False, 'validation_error', f'متن پست LinkedIn نباید بیشتر از {MAX_COMMENTARY_LENGTH} نویسه باشد.'

    attachments = attachments or []
    # LinkedIn does not support standalone voice/audio attachments
    voice_present = any(a.get('media_type') == 'voice' for a in attachments)
    usable = [a for a in attachments if a.get('media_type') in ('image', 'video', 'document')]

    media_urn = None
    if usable:
        # A single-media post accepts one image, video, or document.
        video = next((a for a in usable if a.get('media_type') == 'video'), None)
        document = next((a for a in usable if a.get('media_type') == 'document'), None)
        chosen = video or document or usable[0]
        file_path = _resolve_media_path_or_url(chosen.get('file_path', ''))
        if not file_path:
            return False, 'unknown', 'مسیر فایل نامعتبر است'
        media_urn, err = _upload_asset_for_channel(access_token, author_urn, file_path, chosen.get('media_type'))
        if err:
            return False, 'unknown', err
    elif content.image:
        # Fallback to legacy content image
        file_path = _resolve_media_path_or_url(content.image.name)
        if not file_path:
            return False, 'unknown', 'مسیر تصویر نامعتبر است'
        media_urn, err = _upload_asset_for_channel(access_token, author_urn, file_path, 'image')
        if err:
            return False, 'unknown', err
    elif voice_present:
        return False, 'unsupported_media', 'لینکدین امکان انتشار فایل صوتی مستقل را پشتیبانی نمی‌کند.'

    payload = {
        'author': author_urn,
        'commentary': commentary,
        'visibility': 'PUBLIC',
        'lifecycleState': 'PUBLISHED',
        'distribution': {
            'feedDistribution': 'MAIN_FEED',
            'targetEntities': [],
            'thirdPartyDistributionChannels': [],
        },
    }
    if media_urn:
        payload['content'] = {
            'media': {
                'id': media_urn,
            }
        }
        if usable and chosen.get('media_type') == 'document':
            payload['content']['media']['title'] = chosen.get('original_filename') or 'Document'

    try:
        resp = requests.post(
            'https://api.linkedin.com/rest/posts',
            headers=_headers(access_token),
            json=payload,
            timeout=20,
        )
        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            err_text = str(detail)[:500]
            error_type, user_msg = _classify_error(err_text, resp.status_code)
            if error_type == 'auth_error':
                conn.status = 'needs_reauth'
                conn.save(update_fields=['status'])
            return False, error_type, user_msg

        # LinkedIn returns 201 with x-restli-id header on success
        post_id = resp.headers.get('x-restli-id') or resp.headers.get('X-RestLi-Id')
        return True, None, post_id
    except requests.exceptions.RequestException:
        logger.exception('LinkedIn post request failed')
        return False, 'connection_error', 'ارتباط با LinkedIn برقرار نشد. لطفاً دوباره تلاش کنید.'
    except Exception:
        logger.exception('Unexpected LinkedIn publishing failure')
        return False, 'unknown', 'انتشار در LinkedIn با خطای پیش‌بینی‌نشده مواجه شد.'


def refresh_token_if_needed(connection: LinkedInConnection):
    """Refresh an expiring token under a database row lock."""
    try:
        with transaction.atomic():
            locked = LinkedInConnection.objects.select_for_update().get(pk=connection.pk)
            if locked.access_token_expires_at and locked.access_token_expires_at > timezone.now() + timedelta(days=5):
                connection.access_token = locked.access_token
                connection.access_token_expires_at = locked.access_token_expires_at
                return True
            if not locked.refresh_token:
                return False

            refresh_token = decrypt_token(locked.refresh_token)
            client_id = getattr(settings, 'LINKEDIN_CLIENT_ID', '')
            client_secret = getattr(settings, 'LINKEDIN_CLIENT_SECRET', '')
            if not refresh_token or not client_id or not client_secret:
                locked.status = 'needs_reauth'
                locked.save(update_fields=['status'])
                return False

            resp = requests.post(
                'https://www.linkedin.com/oauth/v2/accessToken',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'client_id': client_id,
                    'client_secret': client_secret,
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=15,
            )
            data = resp.json()
            if not resp.ok or 'access_token' not in data:
                locked.status = 'needs_reauth'
                locked.save(update_fields=['status'])
                return False

            from channels_app.crypto import encrypt_token
            locked.access_token = encrypt_token(data['access_token'])
            if data.get('refresh_token'):
                locked.refresh_token = encrypt_token(data['refresh_token'])
                if data.get('refresh_token_expires_in'):
                    locked.refresh_token_expires_at = timezone.now() + timedelta(seconds=int(data['refresh_token_expires_in']))
            expires_in = data.get('expires_in', 5184000)
            locked.access_token_expires_at = timezone.now() + timedelta(seconds=int(expires_in))
            locked.status = 'active'
            locked.save()
            connection.access_token = locked.access_token
            connection.refresh_token = locked.refresh_token
            connection.access_token_expires_at = locked.access_token_expires_at
            connection.status = locked.status
        return True
    except Exception:
        logger.exception('LinkedIn token refresh failed for connection %s', connection.id)
        connection.status = 'needs_reauth'
        connection.save(update_fields=['status'])
        return False


def refresh_all_linkedin_tokens():
    """Daily job: refresh tokens expiring soon."""
    threshold = timezone.now() + timedelta(days=5)
    connections = LinkedInConnection.objects.filter(
        is_active=True,
        status='active',
        access_token_expires_at__lte=threshold,
    )
    for conn in connections:
        refresh_token_if_needed(conn)
        time.sleep(0.2)
