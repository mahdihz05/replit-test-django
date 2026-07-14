import requests
import json
import logging
from config.network import telegram_request

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _call(token, method, payload):
    if not token:
        return None, 'توکن ربات تلگرام تنظیم نشده است'
    url = TELEGRAM_API.format(token=token, method=method)
    try:
        resp = telegram_request('POST', url, json=payload, timeout=15)
        data = resp.json()
        if not data.get('ok'):
            desc = data.get('description', 'Unknown error')
            logger.warning(f'Telegram API error ({method}): {desc}')
            return None, desc
        return data.get('result'), None
    except requests.exceptions.ConnectionError as e:
        return None, f'خطا در اتصال به تلگرام: {e}'
    except Exception as e:
        return None, str(e)


def send_message(token, chat_id, text):
    return _call(token, 'sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    })


def delete_message(token, chat_id, message_id):
    result, _ = _call(token, 'deleteMessage', {
        'chat_id': chat_id,
        'message_id': message_id
    })
    return result is not None


def get_chat(token, chat_id):
    result, _ = _call(token, 'getChat', {'chat_id': chat_id})
    return result


def _resolve_media_path(file_path):
    if not file_path:
        return None
    if file_path.startswith('/'):
        return file_path
    from django.conf import settings
    return f"{settings.MEDIA_ROOT.rstrip('/')}/{file_path.lstrip('/')}"


def _classify_error(err):
    error_lower = err.lower()
    if 'forbidden' in error_lower or 'not enough rights' in error_lower:
        if 'kicked' in error_lower or 'removed' in error_lower:
            return 'bot_removed'
        return 'auth_error'
    if 'retry' in error_lower or 'flood' in error_lower:
        return 'rate_limit'
    if 'network' in error_lower or 'connection' in error_lower:
        return 'connection_error'
    return 'unknown'


def _send_media_group(token, chat_id, attachments):
    """Send a group of image/video attachments without any caption."""
    media = []
    files = {}
    for i, att in enumerate(attachments):
        media_type = att.get('media_type')
        full_path = _resolve_media_path(att.get('file_path', ''))
        if not full_path:
            return None, 'مسیر فایل نامعتبر است'
        try:
            files[f'file_{i}'] = open(full_path, 'rb')
        except Exception as e:
            return None, f'خطا در خواندن فایل: {e}'
        tg_type = 'photo' if media_type == 'image' else 'video' if media_type == 'video' else 'document'
        media.append({'type': tg_type, 'media': f'attach://file_{i}'})

    url = TELEGRAM_API.format(token=token, method='sendMediaGroup')
    try:
        resp = telegram_request(
            'POST', url,
            data={'chat_id': chat_id, 'media': json.dumps(media)},
            files=files,
            timeout=120,
        )
        data = resp.json()
        if not data.get('ok'):
            return None, data.get('description', 'Unknown error')
        return data.get('result'), None
    except Exception as e:
        return None, str(e)
    finally:
        for f in files.values():
            try:
                f.close()
            except Exception:
                pass


def _send_single_media(token, chat_id, attachment):
    """Send a single media file without a caption."""
    media_type = attachment.get('media_type')
    full_path = _resolve_media_path(attachment.get('file_path', ''))
    if not full_path:
        return None, 'مسیر فایل نامعتبر است'
    try:
        with open(full_path, 'rb') as f:
            file_data = f.read()
    except Exception as e:
        return None, f'خطا در خواندن فایل: {e}'

    method_map = {
        'image': 'sendPhoto',
        'video': 'sendVideo',
        'voice': 'sendVoice',
        'document': 'sendDocument',
    }
    method = method_map.get(media_type, 'sendDocument')
    file_field = 'photo' if media_type == 'image' else media_type

    url = TELEGRAM_API.format(token=token, method=method)
    try:
        resp = telegram_request(
            'POST', url,
            data={'chat_id': chat_id, 'parse_mode': 'HTML'},
            files={file_field: (attachment.get('original_filename', 'file'), file_data, attachment.get('mime_type', 'application/octet-stream'))},
            timeout=60,
        )
        data = resp.json()
        if not data.get('ok'):
            return None, data.get('description', 'Unknown error')
        return data.get('result'), None
    except Exception as e:
        return None, str(e)


def _send_all_media(token, chat_id, attachments):
    """Send every attachment as media, with no caption. Returns (ok, error_type, first_message_id)."""
    if all(a.get('media_type') in ('image', 'video') for a in attachments):
        first_message_id = None
        for i, chunk in enumerate([attachments[i:i + 10] for i in range(0, len(attachments), 10)]):
            result, err = _send_media_group(token, chat_id, chunk)
            if err:
                return False, _classify_error(err), err
            if i == 0 and isinstance(result, list) and result:
                first_message_id = result[0].get('message_id')
        return True, None, first_message_id

    first_message_id = None
    for att in attachments:
        result, err = _send_single_media(token, chat_id, att)
        if err:
            return False, _classify_error(err), err
        if first_message_id is None and isinstance(result, dict):
            first_message_id = result.get('message_id')
    return True, None, first_message_id


def _send_text(token, chat_id, text):
    """Send a standalone text message. Returns (ok, error_type, message_id_or_error)."""
    result, err = send_message(token, chat_id, text)
    if err:
        return False, _classify_error(err), err
    return True, None, result.get('message_id') if isinstance(result, dict) else None


def publish(channel, content, attachments=None):
    from django.conf import settings
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = channel.external_id

    text = content.body or ''
    if content.title and content.title != 'untitled':
        text = f'<b>{content.title}</b>\n\n{text}'

    attachments = attachments or []

    if not attachments:
        return _send_text(token, chat_id, text)

    # Publish media first with NO caption, then the text as a separate message.
    # This avoids Telegram's caption length limits and keeps the post readable.
    media_ok, media_error_type, media_msg_id = _send_all_media(token, chat_id, attachments)
    if not media_ok:
        return False, media_error_type, media_msg_id

    if text:
        text_ok, text_error_type, text_msg_id = _send_text(token, chat_id, text)
        if not text_ok:
            return False, text_error_type, text_msg_id
        return True, None, media_msg_id or text_msg_id

    return True, None, media_msg_id
