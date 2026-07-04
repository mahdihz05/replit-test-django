import requests
import json
import logging

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _call(token, method, payload):
    if not token:
        return None, 'توکن ربات تلگرام تنظیم نشده است'
    url = TELEGRAM_API.format(token=token, method=method)
    try:
        resp = requests.post(url, json=payload, timeout=15)
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


def send_photo(token, chat_id, text, photo_url):
    return _call(token, 'sendPhoto', {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': text,
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


def _send_media_group(token, chat_id, attachments, caption):
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
        item = {'type': tg_type, 'media': f'attach://file_{i}'}
        if i == 0 and caption:
            item['caption'] = caption
            item['parse_mode'] = 'HTML'
        media.append(item)

    url = TELEGRAM_API.format(token=token, method='sendMediaGroup')
    try:
        resp = requests.post(
            url,
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


def _send_single_media(token, chat_id, text, attachment):
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

    import requests
    url = TELEGRAM_API.format(token=token, method=method)
    try:
        resp = requests.post(
            url,
            data={'chat_id': chat_id, 'caption': text, 'parse_mode': 'HTML'},
            files={file_field: (attachment.get('original_filename', 'file'), file_data, attachment.get('mime_type', 'application/octet-stream'))},
            timeout=60,
        )
        data = resp.json()
        if not data.get('ok'):
            return None, data.get('description', 'Unknown error')
        return data.get('result'), None
    except Exception as e:
        return None, str(e)


def publish(channel, content, attachments=None):
    from django.conf import settings
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = channel.external_id

    text = content.body if content.body else ''
    if content.title and content.title != 'untitled':
        text = f'<b>{content.title}</b>\n\n{text}'

    attachments = attachments or []

    if not attachments:
        result, err = send_message(token, chat_id, text)
        if err:
            error_lower = err.lower()
            if 'forbidden' in error_lower or 'not enough rights' in error_lower:
                if 'kicked' in error_lower or 'removed' in error_lower:
                    return False, 'bot_removed', err
                return False, 'auth_error', err
            if 'retry' in error_lower or 'flood' in error_lower:
                return False, 'rate_limit', err
            if 'network' in error_lower or 'connection' in error_lower:
                return False, 'connection_error', err
            return False, 'unknown', err
        message_id = result.get('message_id') if isinstance(result, dict) else None
        return True, None, message_id

    # All image/video attachments: send in media groups of up to 10 items
    if all(a.get('media_type') in ('image', 'video') for a in attachments):
        first_group = True
        for chunk in [attachments[i:i + 10] for i in range(0, len(attachments), 10)]:
            chunk_caption = text if first_group else ''
            result, err = _send_media_group(token, chat_id, chunk, chunk_caption)
            if err:
                error_lower = err.lower()
                if 'forbidden' in error_lower or 'not enough rights' in error_lower:
                    if 'kicked' in error_lower or 'removed' in error_lower:
                        return False, 'bot_removed', err
                    return False, 'auth_error', err
                if 'retry' in error_lower or 'flood' in error_lower:
                    return False, 'rate_limit', err
                if 'network' in error_lower or 'connection' in error_lower:
                    return False, 'connection_error', err
                return False, 'unknown', err
            first_group = False
        return True, None, None

    # Mixed or single media: send text first, then individual media
    if text:
        msg_result, msg_err = send_message(token, chat_id, text)
        if msg_err:
            error_lower = msg_err.lower()
            if 'forbidden' in error_lower or 'not enough rights' in error_lower:
                if 'kicked' in error_lower or 'removed' in error_lower:
                    return False, 'bot_removed', msg_err
                return False, 'auth_error', msg_err
            if 'retry' in error_lower or 'flood' in error_lower:
                return False, 'rate_limit', msg_err
            if 'network' in error_lower or 'connection' in error_lower:
                return False, 'connection_error', msg_err
            return False, 'unknown', msg_err

    for att in attachments:
        result, err = _send_single_media(token, chat_id, '', att)
        if err:
            return False, 'unknown', err

    return True, None, None
