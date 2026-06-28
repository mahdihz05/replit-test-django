import os
from django.conf import settings


def publish(channel, content):
    try:
        import telegram
        bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
        chat_id = channel.external_id

        if content.image:
            image_path = os.path.join(settings.MEDIA_ROOT, str(content.image))
            with open(image_path, 'rb') as photo:
                bot.send_photo(chat_id=chat_id, photo=photo, caption=content.body)
        else:
            bot.send_message(chat_id=chat_id, text=content.body)

        return True, None, None
    except ConnectionError as e:
        return False, 'connection_error', str(e)
    except Exception as e:
        error_str = str(e).lower()
        if 'forbidden' in error_str or 'not enough rights' in error_str:
            if 'kicked' in error_str or 'removed' in error_str:
                return False, 'bot_removed', str(e)
            return False, 'auth_error', str(e)
        if 'retry' in error_str or 'flood' in error_str:
            return False, 'rate_limit', str(e)
        return False, 'unknown', str(e)
