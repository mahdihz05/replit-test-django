import re
import threading
import logging

logger = logging.getLogger(__name__)


def handle_verification_token(token: str, chat_id: int, chat_title: str, chat_type: str, chat_username: str):
    try:
        from channels_app.models import ChannelVerification, PublishChannel

        verification = ChannelVerification.objects.filter(token=token).first()
        if not verification:
            return None

        if not verification.is_valid():
            return '❌ کد منقضی شده است. لطفاً از پنل کد جدید دریافت کنید.'

        channel, created = PublishChannel.objects.get_or_create(
            workspace=verification.workspace,
            platform=verification.platform,
            external_id=str(chat_id),
            defaults={
                'name': chat_title or str(chat_id),
                'username': chat_username or '',
                'channel_type': chat_type,
                'is_verified': True,
            }
        )

        if not created:
            channel.is_verified = True
            channel.save()

        verification.status = 'verified'
        verification.channel = channel
        verification.save()

        logger.info(f'[Bot] Channel verified: {chat_id} ({chat_title})')
        return '✅ کانال با موفقیت تایید شد!'

    except Exception as e:
        logger.error(f'[Bot] Verification error: {e}')
        return None


def start_bot():
    from django.conf import settings
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        logger.warning('[Bot] TELEGRAM_BOT_TOKEN not set, skipping bot startup')
        return

    def run():
        import asyncio

        async def main():
            try:
                from telegram import Update
                from telegram.ext import Application, MessageHandler, filters

                async def on_message(update: Update, context):
                    if not update.message or not update.message.text:
                        return
                    text = update.message.text.strip()
                    chat = update.effective_chat

                    if re.match(r'^VRF-[A-Z0-9]{8}$', text):
                        reply = handle_verification_token(
                            token=text,
                            chat_id=chat.id,
                            chat_title=chat.title or '',
                            chat_type=chat.type,
                            chat_username=getattr(chat, 'username', '') or '',
                        )
                        if reply:
                            await update.message.reply_text(reply)

                app = Application.builder().token(token).build()
                app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

                logger.info('[Bot] Telegram bot started (polling)')
                async with app:
                    await app.start()
                    await app.updater.start_polling(drop_pending_updates=True)
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
