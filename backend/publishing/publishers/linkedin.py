import requests
import logging
import time
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from channels_app.models import LinkedInConnection
from channels_app.crypto import decrypt_token

logger = logging.getLogger(__name__)

LINKEDIN_API_VERSION = '202605'
RESTLI_VERSION = '2.0.0'


def _headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'LinkedIn-Version': LINKEDIN_API_VERSION,
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
            logger.warning(f'LinkedIn register upload failed: {data}')
            return None, f'خطا در آماده‌سازی آپلود تصویر: {data}'
        value = data.get('value', {})
        return {
            'upload_url': value.get('uploadUrl'),
            'asset_urn': value.get('image'),
        }, None
    except requests.exceptions.RequestException as e:
        return None, f'خطا در اتصال به LinkedIn: {e}'


def _upload_binary(upload_url, image_path_or_url):
    """Step 2: Upload binary image data to the uploadUrl."""
    try:
        if image_path_or_url.startswith('http'):
            media_resp = requests.get(image_path_or_url, timeout=30)
            if not media_resp.ok:
                return False, f'خطا در دانلود تصویر: {media_resp.status_code}'
            image_data = media_resp.content
            content_type = media_resp.headers.get('Content-Type', 'image/jpeg')
        else:
            from django.conf import settings
            full_path = f'{settings.MEDIA_ROOT}{image_path_or_url}'
            with open(full_path, 'rb') as f:
                image_data = f.read()
            content_type = 'image/jpeg'

        resp = requests.put(upload_url, data=image_data, headers={
            'Content-Type': content_type,
        }, timeout=30)
        if not resp.ok:
            return False, f'آپلود تصویر شکست خورد: {resp.status_code}'
        return True, None
    except Exception as e:
        return False, f'خطا در آپلود تصویر: {e}'


def _upload_image_for_channel(channel, content, access_token, owner_urn):
    """Full 3-step image upload for LinkedIn."""
    image_url = None
    if content.image:
        image_url = f'{settings.MEDIA_URL}{content.image}'
    if not image_url:
        return None, None

    meta, err = _register_upload(access_token, owner_urn)
    if err:
        return None, err

    ok, err = _upload_binary(meta['upload_url'], image_url)
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
    return 'unknown', f'انتشار در LinkedIn با خطا مواجه شد: {err_text}'


def publish(channel, content):
    conn = _get_active_connection(channel)
    if not conn:
        return False, 'auth_error', 'اتصال LinkedIn فعال یافت نشد. لطفاً ابتدا متصل شوید.'

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

    media_urn, err = _upload_image_for_channel(channel, content, access_token, author_urn)
    if err:
        return False, 'unknown', err

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
    except requests.exceptions.RequestException as e:
        return False, 'connection_error', f'خطا در اتصال به LinkedIn: {e}'
    except Exception as e:
        return False, 'unknown', f'انتشار در LinkedIn با خطا مواجه شد: {e}'


def refresh_token_if_needed(connection: LinkedInConnection):
    """Try to refresh an access token if it expires within 5 days."""
    if not connection.refresh_token:
        return False
    if connection.access_token_expires_at and connection.access_token_expires_at > timezone.now() + timedelta(days=5):
        return True

    refresh_token = decrypt_token(connection.refresh_token)
    if not refresh_token:
        connection.status = 'needs_reauth'
        connection.save(update_fields=['status'])
        return False

    client_id = getattr(settings, 'LINKEDIN_CLIENT_ID', '')
    client_secret = getattr(settings, 'LINKEDIN_CLIENT_SECRET', '')
    if not client_id or not client_secret:
        return False

    try:
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
            connection.status = 'needs_reauth'
            connection.save(update_fields=['status'])
            return False

        from channels_app.crypto import encrypt_token
        connection.access_token = encrypt_token(data['access_token'])
        if data.get('refresh_token'):
            connection.refresh_token = encrypt_token(data['refresh_token'])
            if data.get('refresh_token_expires_in'):
                connection.refresh_token_expires_at = timezone.now() + timedelta(seconds=int(data['refresh_token_expires_in']))
        expires_in = data.get('expires_in', 5184000)
        connection.access_token_expires_at = timezone.now() + timedelta(seconds=int(expires_in))
        connection.status = 'active'
        connection.save()
        return True
    except Exception as e:
        logger.exception(f'LinkedIn token refresh failed for {connection.id}: {e}')
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
