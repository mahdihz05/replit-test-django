import asyncio
import json
import logging
import re
import requests
import threading
import time
from config.network import telegram_request

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_bot_started = False


def _resolve_name(verification, chat_title):
    """Prefer the chat title from Telegram, but fall back to the user-provided name."""
    return chat_title.strip() or (verification.name or '').strip() or None


def handle_verification_token(token: str, chat_id: int, chat_title: str, chat_type: str, chat_username: str):
    """Mark a pending channel verification as verified and create/activate the channel."""
    try:
        from channels_app.models import ChannelVerification, PublishChannel

        try:
            verification = ChannelVerification.objects.get(token=token)
        except ChannelVerification.DoesNotExist:
            return None

        if not verification.is_valid():
            return '❌ کد منقضی شده است. لطفاً از پنل کد جدید دریافت کنید.'

        channel_name = _resolve_name(verification, chat_title)

        channel, created = PublishChannel.objects.get_or_create(
            workspace=verification.workspace,
            platform=verification.platform,
            external_id=str(chat_id),
            defaults={
                'name': channel_name,
                'username': chat_username or '',
                'channel_type': chat_type or 'channel',
                'is_verified': True,
                'is_active': True,
            }
        )

        if not created:
            # Reactivate soft-deleted channels and refresh metadata.
            channel.is_active = True
            channel.is_verified = True
            channel.name = channel_name or channel.name
            channel.username = chat_username or channel.username or ''
            channel.channel_type = chat_type or channel.channel_type or 'channel'
            channel.save()

        verification.status = 'verified'
        verification.channel = channel
        verification.save()

        logger.info(f'[Bot] Channel verified: {chat_id} ({channel.name})')
        return '✅ کانال با موفقیت تایید شد!'
    except Exception as e:
        logger.error(f'[Bot] Verification error: {e}')
        return None


def _process_message(text: str, chat_id: int, chat_title: str, chat_type: str, chat_username: str):
    """Process a single text message and verify if it contains a VRF token."""
    if not text:
        return None
    match = re.search(r'VRF-[A-Z0-9]{8}', text.strip())
    if match:
        token = match.group(0)
        return handle_verification_token(
            token=token,
            chat_id=chat_id,
            chat_title=chat_title or '',
            chat_type=chat_type,
            chat_username=chat_username or '',
        )
    return None


@csrf_exempt
def telegram_webhook(request):
    """Public webhook endpoint for Telegram updates.

    Handles both normal messages (groups/private) and channel posts, because
    Telegram sends channel messages as `channel_post`, not `message`.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'method not allowed'}, status=405)
    try:
        body = json.loads(request.body)
        logger.debug(f'[Webhook] Received update: {body}')

        # Telegram sends channel posts under the `channel_post` key.
        message = body.get('message') or body.get('channel_post') or body.get('edited_message') or body.get('edited_channel_post') or {}
        text = message.get('text', '') or ''
        chat = message.get('chat', {}) or {}
        chat_id = chat.get('id')
        chat_title = chat.get('title', '')
        chat_type = chat.get('type', '')
        chat_username = chat.get('username', '')

        if text and chat_id:
            logger.info(f'[Webhook] Message from {chat_id} ({chat_type}): {text[:100]}')
            _process_message(text, chat_id, chat_title, chat_type, chat_username)
        else:
            logger.info(f'[Webhook] Ignored update: no text or chat_id. keys={list(body.keys())}')
        return JsonResponse({'ok': True})
    except Exception as e:
        logger.exception(f'[Webhook] Error: {e}')
        return JsonResponse({'ok': False, 'error': 'server error'}, status=500)


def _telegram_api(token: str, method: str, payload: dict = None, timeout: int = 15) -> dict:
    """Call a Telegram Bot API method and return the JSON response."""
    try:
        url = f'https://api.telegram.org/bot{token}/{method}'
        resp = telegram_request('POST', url, json=payload or {}, timeout=timeout)
        return resp.json()
    except Exception as e:
        logger.warning(f'[Bot] Telegram API {method} failed: {e}')
        return {'ok': False, 'description': str(e)}


def _get_webhook_info(token: str) -> dict:
    return _telegram_api(token, 'getWebhookInfo')


def _set_webhook(token: str, webhook_url: str) -> bool:
    """Register the webhook URL with Telegram, retrying on rate limits."""
    for attempt in range(3):
        data = _telegram_api(token, 'setWebhook', {'url': webhook_url, 'drop_pending_updates': True})
        if data.get('ok'):
            logger.info(f'[Bot] Webhook set to {webhook_url}')
            return True
        description = data.get('description', '')
        if 'Too Many Requests' in description:
            retry_after = data.get('parameters', {}).get('retry_after', 1) if isinstance(data.get('parameters'), dict) else 1
            logger.warning(f'[Bot] setWebhook rate limited, retrying after {retry_after}s')
            time.sleep(retry_after + 1)
            continue
        logger.warning(f'[Bot] setWebhook failed: {description}')
        return False
    return False


def _webhook_is_configured(token: str, expected_url: str) -> bool:
    info = _get_webhook_info(token)
    if not info.get('ok'):
        return False
    return info.get('result', {}).get('url') == expected_url


def start_bot():
    """Start the Telegram bot.

    Prefer webhook mode when a public Replit domain (or explicit webhook URL)
    is available, because long-polling from Replit can conflict with stale
    connections after restarts. Fall back to long-polling otherwise.
    """
    from django.conf import settings
    import os
    import time

    global _bot_started
    with _lock:
        if _bot_started:
            return
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not token:
            logger.warning('[Bot] TELEGRAM_BOT_TOKEN not set, skipping bot startup')
            return
        _bot_started = True

    explicit_webhook = getattr(settings, 'TELEGRAM_WEBHOOK_URL', '')
    replit_domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
    webhook_url = explicit_webhook or (f'https://{replit_domain}/api/webhooks/telegram/' if replit_domain else '')

    if webhook_url:
        if _webhook_is_configured(token, webhook_url) or _set_webhook(token, webhook_url):
            logger.info('[Bot] Telegram bot running in webhook mode')
            return
        logger.warning('[Bot] Webhook could not be configured; falling back to long-polling')

    def run():
        async def main():
            try:
                from telegram import Update
                from telegram.ext import Application, MessageHandler, filters
                from telegram.request import HTTPXRequest

                async def on_message(update: Update, context):
                    if not update.effective_message or not update.effective_message.text:
                        return
                    chat = update.effective_chat
                    reply = _process_message(
                        update.effective_message.text,
                        chat.id,
                        chat.title or '',
                        chat.type,
                        getattr(chat, 'username', '') or '',
                    )
                    if reply:
                        await update.effective_message.reply_text(reply)

                trust_env = getattr(settings, 'TELEGRAM_TRUST_ENV_PROXY', False)
                proxy_url = getattr(settings, 'TELEGRAM_PROXY_URL', '') or None
                api_request = HTTPXRequest(
                    proxy=proxy_url,
                    httpx_kwargs={'trust_env': trust_env},
                )
                updates_request = HTTPXRequest(
                    read_timeout=10,
                    proxy=proxy_url,
                    httpx_kwargs={'trust_env': trust_env},
                )
                app = (
                    Application.builder()
                    .token(token)
                    .request(api_request)
                    .get_updates_request(updates_request)
                    .build()
                )
                app.add_handler(
                    MessageHandler(
                        filters.TEXT
                        & ~filters.COMMAND
                        & (filters.UpdateType.MESSAGE | filters.UpdateType.CHANNEL_POST),
                        on_message,
                    )
                )

                logger.info('[Bot] Telegram bot started (long-polling)')
                await app.initialize()
                await app.start()
                await app.updater.start_polling(
                    drop_pending_updates=True,
                    poll_interval=1.0,
                    timeout=5,
                )
                await asyncio.Event().wait()
            except Exception as e:
                logger.error(f'[Bot] Error: {e}')

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()

    t = threading.Thread(target=run, daemon=True, name='telegram-bot')
    t.start()
    logger.info('[Bot] Telegram bot thread launched')
