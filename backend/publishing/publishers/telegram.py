import requests
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


def publish(channel, content):
    from django.conf import settings
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = channel.external_id

    text = content.body if content.body else ''
    if content.title and content.title != 'untitled':
        text = f'<b>{content.title}</b>\n\n{text}'

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
