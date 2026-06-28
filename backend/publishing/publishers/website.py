import requests
from django.conf import settings


def publish(channel, content):
    try:
        extra = channel.extra_data or {}
        webhook_url = extra.get('webhook_url', '')
        api_key = extra.get('api_key', '')

        if not webhook_url:
            return False, 'unknown', 'Webhook URL not configured'

        image_url = None
        if content.image:
            image_url = f'{settings.MEDIA_URL}{content.image}'

        payload = {
            'title': content.title,
            'body': content.body,
            'image_url': image_url,
            'published_at': content.published_at.isoformat() if content.published_at else None,
            'tags': content.tags,
        }

        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)

        if response.status_code >= 400:
            return False, 'unknown', f'HTTP {response.status_code}'

        return True, None, response.json() if response.content else {}
    except ConnectionError as e:
        return False, 'connection_error', str(e)
    except Exception as e:
        return False, 'unknown', str(e)
