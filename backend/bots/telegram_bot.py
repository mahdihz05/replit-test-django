import re
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def handle_message(update, context):
    text = update.message.text or ''
    chat = update.effective_chat

    if re.match(r'^VRF-[A-Z0-9]{8}$', text.strip()):
        token = text.strip()
        try:
            from channels_app.models import ChannelVerification, PublishChannel
            from django.utils import timezone

            verification = ChannelVerification.objects.get(token=token)
            if not verification.is_valid():
                update.message.reply_text('❌ کد منقضی شده است. لطفاً از پنل کد جدید دریافت کنید.')
                return

            channel, created = PublishChannel.objects.get_or_create(
                workspace=verification.workspace,
                platform=verification.platform,
                external_id=str(chat.id),
                defaults={
                    'name': chat.title or str(chat.id),
                    'username': getattr(chat, 'username', '') or '',
                    'channel_type': chat.type,
                    'is_verified': True,
                }
            )

            if not created:
                channel.is_verified = True
                channel.save()

            verification.status = 'verified'
            verification.channel = channel
            verification.save()

            update.message.reply_text('✅ کانال با موفقیت تایید شد')
        except ChannelVerification.DoesNotExist:
            pass
        except Exception as e:
            print(f'Bot error: {e}')


def start_bot():
    from django.conf import settings
    if not settings.TELEGRAM_BOT_TOKEN:
        print('[Bot] Telegram bot token not configured')
        return

    try:
        from telegram.ext import Updater, MessageHandler, Filters
        updater = Updater(token=settings.TELEGRAM_BOT_TOKEN)
        dp = updater.dispatcher
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        updater.start_polling()
        print('[Bot] Telegram bot started')
    except Exception as e:
        print(f'[Bot] Failed to start: {e}')
