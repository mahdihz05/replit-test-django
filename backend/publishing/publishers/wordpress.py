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
    if status_code == 403 or 'forbidden' in err_lower or 'rest_cannot_create' in err_lower:
        return 'auth_error', 'کاربر وردپرس اجازه ساخت این نوع محتوا را ندارد. نقش کاربر یا دسترسی نوع محتوا را بررسی کنید.'
    if status_code == 404 or 'rest_no_route' in err_lower:
        return 'connection_error', 'مسیر انتشار این نوع محتوا در وردپرس در دسترس نیست. اطلاعات سایت را به‌روزرسانی کنید.'
    if status_code == 400:
        return 'unknown', 'وردپرس اطلاعات محتوا را نپذیرفت. عنوان، نامک و طبقه‌بندی‌ها را بررسی کنید.'
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


def discover_capabilities(connection):
    """Discover editable REST content types and their taxonomies without exposing credentials."""
    try:
        auth = _basic_auth(connection)
        root = safe_get(f'{connection.site_url.rstrip("/")}/wp-json/', timeout=15)
        types_resp = safe_get(_api_url(connection.site_url, 'wp/v2/types'), auth=auth,
                              params={'context': 'edit'}, timeout=20)
        tax_resp = safe_get(_api_url(connection.site_url, 'wp/v2/taxonomies'), auth=auth,
                            params={'context': 'edit'}, timeout=20)
        if not types_resp.ok:
            error_type, message = _classify_error(types_resp.text[:300], types_resp.status_code)
            return False, error_type, message

        root_data = root.json() if root.ok else {}
        type_data = types_resp.json()
        tax_data = tax_resp.json() if tax_resp.ok else {}
        excluded = {'attachment', 'wp_block', 'wp_template', 'wp_template_part', 'nav_menu_item'}
        post_types = []
        for slug, item in type_data.items():
            rest_base = item.get('rest_base') or slug
            if slug in excluded or not rest_base:
                continue
            post_types.append({
                'slug': slug,
                'name': item.get('name') or slug,
                'rest_base': rest_base,
                'supports': item.get('supports') or {},
                'taxonomies': item.get('taxonomies') or [],
            })

        taxonomies = {}
        for slug, item in tax_data.items():
            rest_base = item.get('rest_base') or slug
            terms = []
            terms_resp = safe_get(_api_url(connection.site_url, f'wp/v2/{rest_base}'), auth=auth,
                                  params={'per_page': 100, 'orderby': 'name'}, timeout=20)
            if terms_resp.ok:
                terms = [{'id': term.get('id'), 'name': term.get('name'), 'parent': term.get('parent', 0)}
                         for term in terms_resp.json()]
            taxonomies[slug] = {
                'slug': slug,
                'name': item.get('name') or slug,
                'rest_base': rest_base,
                'hierarchical': bool(item.get('hierarchical')),
                'types': item.get('types') or [],
                'terms': terms,
            }

        return True, None, {
            'site_name': root_data.get('name') or connection.site_url,
            'capabilities': {
                'post_types': sorted(post_types, key=lambda value: (value['slug'] not in ('post', 'page'), value['name'])),
                'taxonomies': taxonomies,
            },
        }
    except requests.exceptions.RequestException:
        return False, 'connection_error', 'اتصال به سایت وردپرس برقرار نشد. در دسترس بودن سایت و HTTPS را بررسی کنید.'
    except Exception:
        logger.exception('WordPress capability discovery failed')
        return False, 'unknown', 'دریافت اطلاعات سایت وردپرس ناموفق بود. دوباره تلاش کنید.'


def validate_publish_options(connection, options):
    options = options if isinstance(options, dict) else {}
    post_type = str(options.get('post_type') or 'post')
    publish_status = str(options.get('status') or 'draft')
    if publish_status not in {'draft', 'pending', 'publish'}:
        return None, 'وضعیت انتخاب‌شده وردپرس معتبر نیست.'
    post_types = (connection.capabilities or {}).get('post_types') or []
    selected = next((item for item in post_types if item.get('slug') == post_type), None)
    if post_types and not selected:
        return None, 'نوع محتوای انتخاب‌شده دیگر در سایت موجود نیست. اطلاعات سایت را به‌روزرسانی کنید.'
    selected = selected or {'slug': 'post', 'rest_base': 'posts', 'supports': {}, 'taxonomies': ['category', 'post_tag']}
    return {
        'post_type': selected['slug'],
        'rest_base': selected.get('rest_base') or selected['slug'],
        'status': publish_status,
        'excerpt': str(options.get('excerpt') or '').strip(),
        'slug': str(options.get('slug') or '').strip(),
        'taxonomy_terms': options.get('taxonomy_terms') if isinstance(options.get('taxonomy_terms'), dict) else {},
        'featured_attachment_id': str(options.get('featured_attachment_id') or ''),
        'supports': selected.get('supports') or {},
        'taxonomies': selected.get('taxonomies') or [],
    }, None


def publish(channel, content, attachments=None, options=None):
    conn = _get_active_connection(channel)
    if not conn:
        return False, 'auth_error', 'اتصال وردپرس فعال یافت نشد. لطفاً ابتدا متصل شوید.'

    password = decrypt_token(conn.application_password)
    if not password:
        conn.status = 'invalid'
        conn.save(update_fields=['status'])
        return False, 'auth_error', 'اعتبار اتصال وردپرس قابل خواندن نیست. لطفاً دوباره متصل شوید.'

    publish_options, option_error = validate_publish_options(conn, options)
    if option_error:
        return False, 'unknown', option_error

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
        media_info['source_attachment_id'] = str(att.get('id') or '')
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
        requested_featured = publish_options.get('featured_attachment_id')
        first_image = next((m for m in media_list if m.get('media_type') == 'image' and
                            requested_featured and m.get('source_attachment_id') == requested_featured), None)
        first_image = first_image or next((m for m in media_list if m.get('media_type') == 'image'), None)
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
        'status': publish_options['status'],
    }
    supports = publish_options.get('supports') or {}
    if supports and not supports.get('title'):
        payload.pop('title', None)
    if supports and not supports.get('editor'):
        payload.pop('content', None)
    if publish_options['excerpt'] and (not supports or supports.get('excerpt')):
        payload['excerpt'] = publish_options['excerpt']
    if publish_options['slug']:
        payload['slug'] = publish_options['slug']
    if featured_id and (not supports or supports.get('thumbnail')):
        payload['featured_media'] = featured_id

    taxonomies = (conn.capabilities or {}).get('taxonomies') or {}
    for taxonomy_slug, term_ids in publish_options['taxonomy_terms'].items():
        if taxonomy_slug not in publish_options['taxonomies'] or not isinstance(term_ids, list):
            continue
        taxonomy = taxonomies.get(taxonomy_slug) or {}
        rest_base = taxonomy.get('rest_base') or taxonomy_slug
        payload[rest_base] = [int(term_id) for term_id in term_ids if str(term_id).isdigit()]

    # Preserve automatic content tags when the user did not explicitly choose tags.
    tags = content.tags or []
    if tags and 'post_tag' in publish_options['taxonomies'] and 'tags' not in payload:
        tag_ids = _resolve_tag_ids(conn, tags)
        if tag_ids:
            payload['tags'] = tag_ids

    try:
        resp = safe_post(
            _api_url(conn.site_url, f"wp/v2/{publish_options['rest_base']}"),
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
        return True, None, {
            'post_id': post_id,
            'url': post_url,
            'edit_url': f'{conn.site_url.rstrip("/")}/wp-admin/post.php?post={post_id}&action=edit' if post_id else '',
            'status': data.get('status') or publish_options['status'],
            'post_type': publish_options['post_type'],
        }
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
        # Some hosting security rules block the pretty /wp-json/.../users/me
        # path at the web-server layer while WordPress' equivalent index.php
        # REST route remains available. This is an official REST routing form
        # and still requires the same Application Password authentication.
        content_type = (resp.headers.get('Content-Type') or '').lower()
        if resp.status_code in (403, 404) and 'application/json' not in content_type:
            resp = safe_get(
                f'{connection.site_url.rstrip("/")}/',
                auth=_basic_auth(connection),
                params={'rest_route': '/wp/v2/users/me', 'context': 'edit'},
                timeout=15,
            )
        return resp.ok
    except Exception as e:
        logger.warning(f'WordPress credential validation failed: {e}')
        return False
