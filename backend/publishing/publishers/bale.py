import os
import requests
from django.conf import settings


def publish(channel, content):
    try:
        base_url = f'https://tapi.bale.ai/bot{settings.BALE_BOT_TOKEN}'
        chat_id = channel.external_id

        if content.image:
            image_path = os.path.join(settings.MEDIA_ROOT, str(content.image))
            with open(image_path, 'rb') as photo:
                response = requests.post(
                    f'{base_url}/sendPhoto',
                    data={'chat_id': chat_id, 'caption': content.body},
                    files={'photo': photo},
                    timeout=30
                )
        else:
            response = requests.post(
                f'{base_url}/sendMessage',
                json={'chat_id': chat_id, 'text': content.body},
                timeout=30
            )

        data = response.json()
        if not data.get('ok'):
            return False, 'unknown', str(data)

        return True, None, data
    except ConnectionError as e:
        return False, 'connection_error', str(e)
    except Exception as e:
        return False, 'unknown', str(e)
