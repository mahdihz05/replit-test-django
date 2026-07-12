import logging
import re
import requests
import threading
import time

from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_bale_started = False

BALE_API = "https://tapi.bale.ai/bot{token}/{method}"

TOKEN_RE = re.compile(r'^VRF-[A-Z0-9]{8}$')


def _bale_call(token, method, payload):
    url = BALE_API.format(token=token, method=method)
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if not data.get('ok'):
            return None, data.get('description', 'Unknown error')
        return data.get('result'), None
    except Exception as e:
        return None, str(e)


def _process_bale_update(token, update):
    """Process a single Bale update and verify channels."""
    message = update.get('message', {})
    text = (message.get('text') or '').strip()
    chat = message.get('chat', {})
    chat_id = chat.get('id')
    chat_title = chat.get('title', '')
    chat_type = chat.get('type', '')
    chat_username = chat.get('username', '')

    if not text or not chat_id or not TOKEN_RE.match(text):
        return

    from .telegram_bot import handle_verification_token
    reply = handle_verification_token(
        token=text,
        chat_id=chat_id,
        chat_title=chat_title,
        chat_type=chat_type,
        chat_username=chat_username,
    )
    if reply:
        _bale_call(token, 'sendMessage', {'chat_id': chat_id, 'text': reply})


def start_bale_bot():
    """Start a long-polling bot for Bale Messenger in a daemon thread."""
    global _bale_started
    with _lock:
        if _bale_started:
            return
        token = getattr(settings, 'BALE_BOT_TOKEN', None)
        if not token:
            logger.warning('[Bale Bot] BALE_BOT_TOKEN not set, skipping bot startup')
            return
        _bale_started = True

    def run():
        offset = 0
        while True:
            try:
                result, err = _bale_call(token, 'getUpdates', {
                    'offset': offset,
                    'limit': 100,
                    'timeout': 5,
                })
                if err:
                    logger.error(f'[Bale Bot] getUpdates error: {err}')
                    time.sleep(5)
                    continue

                updates = result or []
                for update in updates:
                    update_id = update.get('update_id')
                    if update_id is not None and update_id >= offset:
                        offset = update_id + 1
                    _process_bale_update(token, update)

                time.sleep(1)
            except Exception as e:
                logger.error(f'[Bale Bot] Error: {e}')
                time.sleep(5)

    t = threading.Thread(target=run, daemon=True, name='bale-bot')
    t.start()
    logger.info('[Bale Bot] Bale bot thread launched')
