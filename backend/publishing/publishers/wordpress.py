import os
import requests
import logging
import mimetypes
from django.conf import settings
from urllib.parse import urljoin, urlparse
from channels_app.models import WordPressConnection
from channels_app.crypto import decrypt_token
from channels_app.validators import is_safe_url, safe_get, safe_post

logger = logging.getLogger(__name__)


def _get_active_connection(channel):
    try:
        return WordPressConnection.objects.get(
            workspace=channel.workspace,
            site_url=channel.external_id,
            is_active=True,
            status='active',
        )
    except WordPressConnection.DoesNotExist:
        return None


def _api_url(site_url, path):
    base = site_url.rstrip('/')
    return f'{base}/wp-json/{path}'


def _basic_auth(connection):
    password = decrypt_token(connection.application_password)
    return (connection.wp_username, password)


def _classify_error(err_text, status_code):
    err_lower = (err_text or '').lower()
    if status_code == 401 or 'unauthorized' in err_lower or 'incorrect password' in err_lower:
        return 'auth_error', 'اعتبار اتصال وردپرس نامعتبر است. لطفاً دوباره متصل شوید.'
    if status_code >= 500 or 'connection' in err_lower or 'timeout' in err_lower:
        return 'connection_error', 'خطا در اتصال به سایت وردپرس. لطفاً دوباره تلاش کنید.'
    return 'unknown', f'انتشار در وردپرس با خطا مواجه شد: {err_text}'


def _resolve_media_path_or_url(file_path):
    if not file_path:
        return None
    if file_path.startswith('http'):
        return file_path
    return f"{settings.MEDIA_ROOT.rstrip('/')}/{file_path.lstrip('/')}"


def _upload_media_to_wordpress(connection, file_path, original_filename, mime_type, media_type):
    try:
        resolved_path = _resolve_media_path_or_url(file_path)
        if not resolved_path:
            return None, 'مسیر فایل نامعتبر است'
        if resolved_path.startswith('http'):
            media_resp = safe_get(resolved_path, timeout=30)
            if not media_resp.ok:
                return None, f'خطا در دانلود فایل: {media_resp.status_code}'
            file_data = media_resp.content
            content_type = media_resp.headers.get('Content-Type') or mime_type or 'application/octet-stream'
            filename = urlparse(resolved_path).path.split('/')[-1] or original_filename or 'file'
        else:
            with open(resolved_path, 'rb') as f:
                file_data = f.read()
            content_type = mime_type or mimetypes.guess_type(resolved_path)[0] or 'application/octet-stream'
            filename = resolved_path.split('/')[-1] or original_filename or 'file'

        auth = _basic_auth(connection)
        resp = safe_post(
            _api_url(connection.site_url, 'wp/v2/media'),
            auth=auth,
            files={'file': (filename, file_data, content_type)},
            timeout=120,
        )
        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            return None, f'آپلود فایل شکست خورد: {detail}'
        data = resp.json()
        return {
            'id': data.get('id'),
            'url': data.get('source_url'),
            'mime_type': data.get('mime_type'),
            'media_type': media_type,
        }, None
    except Exception as e:
        return None, f'خطا در آپلود فایل: {e}'


def _embed_wordpress_media(body, media_list):
    """Append media embeds to post body."""
    if not media_list:
        return body
    blocks = []
    for m in media_list:
        mt = m.get('media_type')
        url = m.get('url') or ''
        if mt == 'image':
            blocks.append(f'<figure class="wp-block-image"><img src="{url}" alt="" /></figure>')
        elif mt == 'video':
            blocks.append(f'<figure class="wp-block-video"><video controls src="{url}"></video></figure>')
        elif mt == 'voice':
            blocks.append(f'<figure class="wp-block-audio"><audio controls src="{url}"></audio></figure>')
        elif mt == 'document':
            blocks.append(f'<p><a href="{url}" download>دانلود فایل</a></p>')
    return body + '\n\n' + '\n\n'.join(blocks) if body else '\n\n'.join(blocks)


def publish(channel, content, attachments=None):
    conn = _get_active_connection(channel)
    if not conn:
        return False, 'auth_error', 'اتصال وردپرس فعال یافت نشد. لطفاً ابتدا متصل شوید.'

    password = decrypt_token(conn.application_password)
    if not password:
        conn.status = 'invalid'
        conn.save(update_fields=['status'])
        return False, 'auth_error', 'اعتبار اتصال وردپرس قابل خواندن نیست. لطفاً دوباره متصل شوید.'

    attachments = attachments or []
    media_list = []
    for att in attachments:
        file_path = att.get('file_path', '')
        media_info, err = _upload_media_to_wordpress(
            conn, file_path, att.get('original_filename'), att.get('mime_type'), att.get('media_type')
        )
        if err:
            logger.warning(f'WordPress media upload failed: {err}')
            continue
        media_list.append(media_info)

    # Legacy featured image fallback
    featured_id = None
    if content.image and not any(m.get('media_type') == 'image' for m in media_list):
        image_path = _resolve_media_path_or_url(content.image.name)
        if image_path:
            media_info, err = _upload_media_to_wordpress(
                conn, image_path,
                os.path.basename(content.image.name), 'image/jpeg', 'image'
            )
            if media_info:
                media_list.append(media_info)

    if media_list:
        first_image = next((m for m in media_list if m.get('media_type') == 'image'), None)
        if first_image:
            featured_id = first_image.get('id')

    body = content.body or ''
    if content.title and content.title not in ('untitled', ''):
        title = content.title
    else:
        title = body[:100] if body else 'پست محتوایار'

    body = _embed_wordpress_media(body, media_list)

    payload = {
        'title': title,
        'content': body,
        'status': 'publish',
    }
    if featured_id:
        payload['featured_media'] = featured_id

    # optionally attach categories/tags if available
    tags = content.tags or []
    if tags:
        tag_ids = _resolve_tag_ids(conn, tags)
        if tag_ids:
            payload['tags'] = tag_ids

    try:
        resp = safe_post(
            _api_url(conn.site_url, 'wp/v2/posts'),
            auth=_basic_auth(conn),
            json=payload,
            timeout=30,
        )
        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            err_text = str(detail)[:500]
            error_type, user_msg = _classify_error(err_text, resp.status_code)
            if error_type == 'auth_error':
                conn.status = 'invalid'
                conn.save(update_fields=['status'])
            return False, error_type, user_msg

        data = resp.json()
        post_id = data.get('id')
        post_url = data.get('link')
        return True, None, {'post_id': post_id, 'url': post_url}
    except requests.exceptions.RequestException as e:
        logger.warning(f'WordPress publish request failed: {e}')
        return False, 'connection_error', f'اتصال به سایت وردپرس برقرار نشد: {e}'
    except Exception as e:
        return False, 'unknown', f'انتشار در وردپرس با خطا مواجه شد: {e}'


def _resolve_tag_ids(connection, tags):
    """Try to find existing tags; if missing, create them. Return list of IDs."""
    auth = _basic_auth(connection)
    tag_ids = []
    for tag in tags:
        if not tag or not isinstance(tag, str):
            continue
        try:
            search = safe_get(
                _api_url(connection.site_url, 'wp/v2/tags'),
                auth=auth,
                params={'search': tag, 'per_page': 1},
                timeout=15,
            )
            if search.ok:
                results = search.json()
                if results:
                    tag_ids.append(results[0]['id'])
                    continue
            create = safe_post(
                _api_url(connection.site_url, 'wp/v2/tags'),
                auth=auth,
                json={'name': tag},
                timeout=15,
            )
            if create.ok:
                tag_ids.append(create.json().get('id'))
        except Exception as e:
            logger.warning(f'WordPress tag resolution failed for {tag}: {e}')
    return tag_ids


def check_application_passwords(site_url):
    """Return (ok, error_message) after checking whether the site supports Application Passwords."""
    if not is_safe_url(site_url):
        return False, 'آدرس سایت نامعتبر یا غیرمجاز است.'
    try:
        resp = safe_get(
            f'{site_url.rstrip("/")}/wp-json/',
            timeout=15,
            headers={'Accept': 'application/json'},
        )
        if not resp.ok:
            return False, 'این سایت وردپرس از این روش اتصال پشتیبانی نمی‌کند. لطفاً از یک سایت وردپرس اختصاصی (self-hosted) یا پلن Business به بالای WordPress.com استفاده کنید.'
        data = resp.json()
        auth = data.get('authentication', {})
        if 'application-passwords' not in auth:
            return False, 'این سایت وردپرس از این روش اتصال پشتیبانی نمی‌کند. لطفاً از یک سایت وردپرس اختصاصی (self-hosted) یا پلن Business به بالای WordPress.com استفاده کنید.'
        return True, None
    except requests.exceptions.RequestException as e:
        return False, f'اتصال به سایت وردپرس برقرار نشد: {e}'
    except Exception as e:
        return False, f'بررسی سایت وردپرس با خطا مواجه شد: {e}'


def validate_credentials(connection):
    """Test credentials by calling /wp/v2/users/me?context=edit."""
    try:
        resp = safe_get(
            _api_url(connection.site_url, 'wp/v2/users/me'),
            auth=_basic_auth(connection),
            params={'context': 'edit'},
            timeout=15,
        )
        return resp.ok
    except Exception as e:
        logger.warning(f'WordPress credential validation failed: {e}')
        return False
