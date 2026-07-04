import os
import json
import logging
import secrets
from datetime import timedelta
from cryptography.fernet import Fernet, InvalidToken
from django.core.signing import TimestampSigner, BadSignature
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_key() -> bytes:
    """Return the Fernet key used for encrypting tokens."""
    key = (
        os.environ.get('SHARED_TOKEN_ENCRYPTION_KEY')
        or os.environ.get('LINKEDIN_TOKEN_ENCRYPTION_KEY')
    )
    if not key:
        # Fallback to deriving a key from Django SECRET_KEY. This is not ideal
        # for production but keeps the app functional when no env var is set.
        import base64
        import hashlib
        derived = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(derived).decode()
        logger.warning(
            'No SHARED_TOKEN_ENCRYPTION_KEY or LINKEDIN_TOKEN_ENCRYPTION_KEY set; '
            'using derived key from SECRET_KEY. Set one of the env vars for production.'
        )
    return key.encode() if isinstance(key, str) else key


def _fernet() -> Fernet:
    return Fernet(_get_key())


def encrypt_token(value: str) -> str:
    if not value:
        return ''
    return _fernet().encrypt(value.encode()).decode()


def decrypt_token(value: str) -> str:
    if not value:
        return ''
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        logger.error('Failed to decrypt token; encryption key may have changed')
        return ''


# Public signed state for OAuth callbacks (works across processes)
_state_signer = TimestampSigner()
STATE_MAX_AGE_SECONDS = 600  # 10 minutes


def sign_state(payload: dict) -> str:
    """
    Sign OAuth state with a TTL and a one-time nonce. The nonce is stored in
    the cache so that replay attempts are rejected even if the signature is valid.
    """
    nonce = secrets.token_urlsafe(32)
    payload['_nonce'] = nonce
    cache_key = f'oauth_nonce:{nonce}'
    cache.set(cache_key, True, timeout=STATE_MAX_AGE_SECONDS)
    return _state_signer.sign(json.dumps(payload, sort_keys=True, default=str))


def unsign_state(value: str) -> dict | None:
    """Validate a signed state, enforcing TTL and one-time nonce consumption."""
    try:
        raw = _state_signer.unsign(value, max_age=STATE_MAX_AGE_SECONDS)
        payload = json.loads(raw)
        nonce = payload.pop('_nonce', None)
        if not nonce:
            return None
        cache_key = f'oauth_nonce:{nonce}'
        if not cache.get(cache_key):
            return None
        cache.delete(cache_key)
        return payload
    except (BadSignature, json.JSONDecodeError):
        return None
