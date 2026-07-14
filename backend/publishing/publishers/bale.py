import requests
import logging

logger = logging.getLogger(__name__)

BALE_API = "https://tapi.bale.ai/bot{token}/{method}"


def _call(token, method, payload):
    if not token:
        return None, 'توکن ربات بله تنظیم نشده است'
    url = BALE_API.format(token=token, method=method)
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if not data.get('ok'):
            desc = data.get('description', 'Unknown error')
            logger.warning(f'Bale API error ({method}): {desc}')
            return None, desc
        return data.get('result'), None
    except requests.exceptions.ConnectionError as e:
        return None, f'خطا در اتصال به بله: {e}'
    except Exception as e:
        return None, str(e)


def send_message(token, chat_id, text):
    return _call(token, 'sendMessage', {
        'chat_id': chat_id,
        'text': text
    })


def send_photo(token, chat_id, text, photo_url):
    return _call(token, 'sendPhoto', {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': text
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


def _send_single_media(token, chat_id, text, attachment):
    media_type = attachment.get('media_type')
    full_path = attachment.get('file_path', '')
    if not full_path.startswith('/'):
        from django.conf import settings
        full_path = f"{settings.MEDIA_ROOT}/{full_path}"
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
    url = BALE_API.format(token=token, method=method)
    try:
        resp = requests.post(
            url,
            data={'chat_id': chat_id, 'caption': text},
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
    token = getattr(settings, 'BALE_BOT_TOKEN', None)
    chat_id = channel.external_id

    # The title is internal workspace metadata, not part of social post copy.
    # AI drafts frequently use the original request as their internal title.
    text = content.body if content.body else ''

    attachments = attachments or []

    if not attachments:
        result, err = send_message(token, chat_id, text)
        if err:
            error_lower = err.lower()
            if 'forbidden' in error_lower:
                return False, 'auth_error', err
            if 'network' in error_lower or 'connection' in error_lower:
                return False, 'connection_error', err
            return False, 'unknown', err
        message_id = result.get('message_id') if isinstance(result, dict) else None
        return True, None, message_id

    if text:
        msg_result, msg_err = send_message(token, chat_id, text)
        if msg_err:
            error_lower = msg_err.lower()
            if 'forbidden' in error_lower:
                return False, 'auth_error', msg_err
            if 'network' in error_lower or 'connection' in error_lower:
                return False, 'connection_error', msg_err
            return False, 'unknown', msg_err

    for att in attachments:
        result, err = _send_single_media(token, chat_id, '', att)
        if err:
            return False, 'unknown', err

    return True, None, None
