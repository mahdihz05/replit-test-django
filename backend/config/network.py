"""Network helpers for services that must not inherit a broken host proxy."""

import requests
from django.conf import settings


def telegram_request(method, url, **kwargs):
    """Call Telegram with explicit proxy behavior.

    Local development environments may set HTTP(S)_PROXY for sandboxing.  The
    Telegram Bot API should connect directly by default; deployments that need
    a real outbound proxy can opt back in with TELEGRAM_TRUST_ENV_PROXY=true.
    """
    with requests.Session() as session:
        session.trust_env = getattr(settings, 'TELEGRAM_TRUST_ENV_PROXY', False)
        proxy_url = getattr(settings, 'TELEGRAM_PROXY_URL', '')
        if proxy_url:
            kwargs.setdefault('proxies', {'http': proxy_url, 'https': proxy_url})
        return session.request(method, url, **kwargs)
