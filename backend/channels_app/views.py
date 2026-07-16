import random
import string
import requests
import logging
import json
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urljoin, urlparse
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from workspaces.models import WorkspaceMember
from .models import (
    PublishChannel, ChannelVerification, LinkedInConnection, LinkedInOAuthState,
    WordPressConnection,
)
from .serializers import (
    PublishChannelSerializer, ChannelVerificationSerializer,
    LinkedInConnectionSerializer, WordPressConnectionSerializer,
)
from .crypto import encrypt_token, decrypt_token, sign_state, unsign_state
from .validators import is_safe_url, normalize_site_url
from publishing.publishers import wordpress as wp_publisher

logger = logging.getLogger(__name__)


def _safe_frontend_origin(value, request=None):
    """Return an allow-listed HTTP(S) origin suitable for postMessage."""
    candidates = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
    if request:
        request_origin = request.headers.get('Origin', '')
        if request_origin:
            candidates.add(request_origin)
    parsed = urlparse(value or '')
    normalized = f'{parsed.scheme}://{parsed.netloc}' if parsed.scheme in ('http', 'https') and parsed.netloc else ''
    return normalized if normalized in candidates else ''


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


# ─────────────────────────────────────────────
# OAuth helpers
# ─────────────────────────────────────────────

def _oauth_callback_html(success, message, platform, origin='*', payload=None):
    """Return a small HTML page that notifies the opener window via postMessage."""
    data = json.dumps({
        'success': success,
        'message': message,
        'platform': platform,
        'payload': payload or {},
    }, ensure_ascii=False)
    target_origin = origin if origin and origin != '*' else 'null'
    target_json = json.dumps(target_origin)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{platform} OAuth</title></head>
<body><p>در حال بستن پنجره...</p>
<script>
try {{
  if (window.opener && {target_json} !== 'null') window.opener.postMessage({data}, {target_json});
}} catch (e) {{}}
window.close();
</script>
</body></html>"""
    return HttpResponse(html, content_type='text/html; charset=utf-8')


# ─────────────────────────────────────────────
# Generic channels
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def channel_list(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    channels = PublishChannel.objects.filter(workspace_id=workspace_id, is_active=True)

    platform = request.GET.get('platform')
    if platform:
        channels = channels.filter(platform=platform)

    verified = request.GET.get('verified')
    if verified == 'true':
        channels = channels.filter(is_verified=True)

    return Response({'success': True, 'data': PublishChannelSerializer(channels, many=True).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_start(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند کانال اضافه کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    platform = request.data.get('platform', 'telegram')
    channel_name = request.data.get('name', '').strip()
    channel_type = request.data.get('channel_type', 'channel')

    if platform not in ['telegram', 'bale']:
        return Response({'success': False, 'error': 'پلتفرم نامعتبر است', 'code': 'INVALID_PLATFORM'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not channel_name:
        return Response({'success': False, 'error': 'نام کانال الزامی است', 'code': 'NAME_REQUIRED'},
                        status=status.HTTP_400_BAD_REQUEST)

    token = ChannelVerification.generate_token()
    while ChannelVerification.objects.filter(token=token).exists():
        token = ChannelVerification.generate_token()

    verification = ChannelVerification.objects.create(
        workspace_id=workspace_id,
        requested_by=request.user,
        platform=platform,
        name=channel_name,
        channel_type=channel_type,
        token=token,
        expires_at=timezone.now() + timedelta(minutes=10)
    )

    platform_name = 'تلگرام' if platform == 'telegram' else 'بله'
    channel_type_fa = 'کانال' if channel_type == 'channel' else 'گروه'
    instructions = (
        f'۱. ربات {platform_name} ما را به {channel_type_fa} خود اضافه کنید و آن را ادمین کنید.\n'
        f'۲. سپس این کد را در {channel_type_fa} ارسال کنید:\n\n'
        f'{token}\n\n'
        f'۳. پس از ارسال کد، تأیید اتصال به‌صورت خودکار انجام می‌شود.'
    )

    data = ChannelVerificationSerializer(verification).data
    data['name'] = channel_name
    data['channel_type'] = channel_type
    data['instructions'] = instructions

    return Response({'success': True, 'data': data}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_status(request, workspace_id, token):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        verification = ChannelVerification.objects.get(token=token, workspace_id=workspace_id)
    except ChannelVerification.DoesNotExist:
        return Response({'success': False, 'error': 'توکن یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    if verification.status == 'pending' and verification.expires_at < timezone.now():
        verification.status = 'expired'
        verification.save()

    data = ChannelVerificationSerializer(verification).data
    if verification.channel:
        data['channel'] = PublishChannelSerializer(verification.channel).data
    return Response({'success': True, 'data': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_retry(request, workspace_id, token):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        verification = ChannelVerification.objects.get(token=token, workspace_id=workspace_id)
    except ChannelVerification.DoesNotExist:
        return Response({'success': False, 'error': 'توکن یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    new_token = ChannelVerification.generate_token()
    while ChannelVerification.objects.filter(token=new_token).exists():
        new_token = ChannelVerification.generate_token()

    verification.token = new_token
    verification.status = 'pending'
    verification.expires_at = timezone.now() + timedelta(minutes=10)
    verification.save()

    data = ChannelVerificationSerializer(verification).data
    return Response({'success': True, 'data': data})


def _validate_telegram_chat(bot_token, lookup, expected_type):
    """Resolve a chat and prove that this bot can publish to it."""
    from publishing.publishers.telegram import _call

    chat, error = _call(bot_token, 'getChat', {'chat_id': lookup})
    if error or not chat:
        return None, 'ربات به این کانال یا گروه دسترسی ندارد.', 'CHAT_NOT_FOUND'

    actual_type = chat.get('type', '')
    allowed_types = {'channel'} if expected_type == 'channel' else {'group', 'supergroup'}
    if actual_type not in allowed_types:
        expected_label = 'کانال' if expected_type == 'channel' else 'گروه'
        return None, f'شناسه واردشده مربوط به {expected_label} نیست.', 'CHAT_TYPE_MISMATCH'

    bot, error = _call(bot_token, 'getMe', {})
    if error or not bot:
        return None, 'امکان بررسی هویت ربات تلگرام وجود ندارد.', 'BOT_ERROR'

    membership, error = _call(bot_token, 'getChatMember', {
        'chat_id': chat['id'],
        'user_id': bot['id'],
    })
    if error or not membership:
        error_text = str(error or '').lower()
        if any(part in error_text for part in ('user not found', 'participant_id_invalid', 'member not found')):
            return None, 'ابتدا همین ربات نمایش‌داده‌شده را به‌عنوان ادمین کانال یا گروه اضافه کنید.', 'BOT_NOT_ADMIN'
        return None, 'عضویت ربات در کانال قابل بررسی نیست.', 'MEMBERSHIP_CHECK_FAILED'

    if membership.get('status') not in ('administrator', 'creator'):
        return None, 'ابتدا ربات را به‌عنوان ادمین کانال یا گروه اضافه کنید.', 'BOT_NOT_ADMIN'

    if actual_type == 'channel' and not membership.get('can_post_messages', False):
        return None, 'ربات مجوز ارسال پیام در کانال را ندارد.', 'BOT_CANNOT_POST'

    return chat, None, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_manual(request, workspace_id, token):
    """Manually verify a channel using a known chat_id or username.

    Useful when the bot cannot reach the chat (e.g. webhook not set) or the
    user wants to force-confirm a previously sent token.
    """
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند کانال تأیید کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        verification = ChannelVerification.objects.get(token=token, workspace_id=workspace_id)
    except ChannelVerification.DoesNotExist:
        return Response({'success': False, 'error': 'توکن یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    if verification.status == 'verified':
        return Response({'success': True, 'data': {'message': 'کانال قبلاً تأیید شده است'}})

    if not verification.is_valid():
        return Response({'success': False, 'error': 'کد منقضی شده است. لطفاً کد جدید دریافت کنید.', 'code': 'EXPIRED'},
                        status=status.HTTP_400_BAD_REQUEST)

    if verification.platform != 'telegram':
        return Response({
            'success': False,
            'error': 'این روش تأیید فقط برای تلگرام قابل استفاده است',
            'code': 'INVALID_PLATFORM',
        }, status=status.HTTP_400_BAD_REQUEST)

    chat_id = str(request.data.get('chat_id') or '').strip()
    username = (request.data.get('username') or '').strip().lstrip('@')
    if not chat_id and not username:
        return Response({'success': False, 'error': 'chat_id یا username کانال الزامی است', 'code': 'MISSING_CHAT'},
                        status=status.HTTP_400_BAD_REQUEST)

    lookup = chat_id or f'@{username}'

    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not bot_token:
        return Response({'success': False, 'error': 'توکن ربات تلگرام تنظیم نشده است', 'code': 'NOT_CONFIGURED'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    chat, validation_error, validation_code = _validate_telegram_chat(
        bot_token,
        lookup,
        verification.channel_type,
    )
    if validation_error:
        return Response({
            'success': False,
            'error': validation_error,
            'code': validation_code,
        }, status=status.HTTP_400_BAD_REQUEST)
    if not chat:
        return Response({'success': False, 'error': 'ربات به این کانال/گروه دسترسی ندارد', 'code': 'CHAT_NOT_FOUND'},
                        status=status.HTTP_400_BAD_REQUEST)

    from bots.telegram_bot import handle_verification_token
    reply = handle_verification_token(
        token=token,
        chat_id=chat['id'],
        chat_title=chat.get('title', verification.name),
        chat_type=chat.get('type', verification.channel_type),
        chat_username=chat.get('username', ''),
    )
    if not reply:
        return Response({'success': False, 'error': 'تأیید کانال ناموفق بود', 'code': 'VERIFY_FAILED'},
                        status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True, 'data': {'message': reply}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def telegram_bot_status(request, workspace_id):
    """Return the configured Telegram bot identity and whether the token is valid."""
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not bot_token:
        return Response({'success': False, 'error': 'توکن ربات تلگرام تنظیم نشده است', 'code': 'NOT_CONFIGURED'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    from publishing.publishers.telegram import _call
    result, err = _call(bot_token, 'getMe', {})
    if err:
        return Response({'success': False, 'error': err, 'code': 'BOT_ERROR'},
                        status=status.HTTP_502_BAD_GATEWAY)

    return Response({'success': True, 'data': {'bot': result}})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def channel_detail(request, workspace_id, channel_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند کانال حذف کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        channel = PublishChannel.objects.get(id=channel_id, workspace_id=workspace_id)
    except (PublishChannel.DoesNotExist, ValidationError):
        return Response({'success': False, 'error': 'کانال یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    # For LinkedIn/WordPress channels, disconnect the underlying connection record too
    if channel.platform == 'linkedin':
        conn_id = (channel.extra_data or {}).get('connection_id')
        if conn_id:
            LinkedInConnection.objects.filter(id=conn_id, workspace_id=workspace_id).update(
                is_active=False, status='disconnected', access_token='', refresh_token='',
                disconnected_at=timezone.now(),
            )
    elif channel.platform == 'wordpress':
        conn_id = (channel.extra_data or {}).get('connection_id')
        if conn_id:
            WordPressConnection.objects.filter(id=conn_id, workspace_id=workspace_id).update(
                is_active=False, status='disconnected'
            )

    if channel.platform == 'linkedin':
        from publishing.models import PublishJob
        PublishJob.objects.filter(channel=channel, status='queued').update(
            status='failed', completed_at=timezone.now(), next_retry_at=None,
        )

    channel.is_active = False
    channel.save()
    return Response({'success': True, 'data': {'message': 'کانال حذف شد'}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def channel_test(request, workspace_id, channel_id):
    """Send a test message to verify the channel connection is still working."""
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        channel = PublishChannel.objects.get(id=channel_id, workspace_id=workspace_id,
                                             is_active=True, is_verified=True)
    except (PublishChannel.DoesNotExist, ValidationError):
        return Response({'success': False, 'error': 'کانال یافت نشد یا تأیید نشده است', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    from django.conf import settings
    test_text = '✅ اتصال کانال با موفقیت تأیید شد.\nاین یک پیام آزمایشی از سامانه محتوایار است.'

    if channel.platform == 'telegram':
        from publishing.publishers.telegram import send_message
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        result, err = send_message(token, channel.external_id, test_text)
    elif channel.platform == 'bale':
        from publishing.publishers.bale import send_message
        token = getattr(settings, 'BALE_BOT_TOKEN', None)
        result, err = send_message(token, channel.external_id, test_text)
    elif channel.platform == 'wordpress':
        connection_id = (channel.extra_data or {}).get('connection_id')
        connection = WordPressConnection.objects.filter(
            id=connection_id, workspace_id=workspace_id, is_active=True
        ).first()
        if not connection or not wp_publisher.validate_credentials(connection):
            if connection:
                connection.status = 'invalid'
                connection.save(update_fields=['status'])
            return Response({'success': False, 'error': 'اتصال وردپرس معتبر نیست؛ سایت را دوباره متصل کنید.', 'code': 'AUTH_ERROR'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'data': {'message': 'اتصال وردپرس سالم و آماده انتشار است'}})
    else:
        return Response({'success': False, 'error': 'این پلتفرم از تست پشتیبانی نمی‌کند', 'code': 'UNSUPPORTED'},
                        status=status.HTTP_400_BAD_REQUEST)

    if err:
        return Response({'success': False, 'error': err, 'code': 'SEND_FAILED'},
                        status=status.HTTP_502_BAD_GATEWAY)

    return Response({'success': True, 'data': {'message': 'پیام آزمایشی با موفقیت ارسال شد'}})


# ─────────────────────────────────────────────
# LinkedIn OAuth
# ─────────────────────────────────────────────

def _linkedin_redirect_uri(request=None):
    """Return the configured callback, or derive the canonical HTTPS callback."""
    configured = getattr(settings, 'LINKEDIN_REDIRECT_URI', '').strip()
    if configured:
        return configured
    if request is not None:
        return request.build_absolute_uri('/api/auth/linkedin/callback/')
    return ''


def _linkedin_configuration(request=None):
    """Return public configuration health without exposing OAuth credentials."""
    redirect_uri = _linkedin_redirect_uri(request)
    parsed_redirect = urlparse(redirect_uri)
    missing = []
    if not getattr(settings, 'LINKEDIN_CLIENT_ID', '').strip():
        missing.append('LINKEDIN_CLIENT_ID')
    if not getattr(settings, 'LINKEDIN_CLIENT_SECRET', '').strip():
        missing.append('LINKEDIN_CLIENT_SECRET')
    if not redirect_uri:
        missing.append('LINKEDIN_REDIRECT_URI')

    redirect_is_https = parsed_redirect.scheme == 'https' and bool(parsed_redirect.netloc)
    return {
        'configured': not missing and redirect_is_https,
        'credentials_configured': not any(name in missing for name in ('LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET')),
        'redirect_uri': redirect_uri,
        'redirect_is_https': redirect_is_https,
        'api_version': getattr(settings, 'LINKEDIN_API_VERSION', '202606'),
        'missing': missing,
        'required_products': ['Sign In with LinkedIn using OpenID Connect', 'Share on LinkedIn'],
        'required_scopes': ['openid', 'profile', 'email', 'w_member_social'],
    }


def _state_digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def linkedin_connect_start(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند اتصال اضافه کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    linkedin_config = _linkedin_configuration(request)
    if linkedin_config['missing']:
        missing = '، '.join(linkedin_config['missing'])
        return Response({
            'success': False,
            'error': f'تنظیمات LinkedIn در سرور کامل نیست: {missing}',
            'code': 'NOT_CONFIGURED',
            'data': linkedin_config,
        },
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if not linkedin_config['redirect_is_https']:
        return Response({
            'success': False,
            'error': 'آدرس Callback لینکدین باید یک آدرس کامل HTTPS باشد',
            'code': 'REDIRECT_URI_REQUIRES_HTTPS',
            'data': linkedin_config,
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    client_id = getattr(settings, 'LINKEDIN_CLIENT_ID', '').strip()

    target = request.data.get('platform_target', 'personal')
    if target not in dict(LinkedInConnection.TARGET_CHOICES):
        return Response({'success': False, 'error': 'هدف انتشار معتبر نیست', 'code': 'INVALID_TARGET'},
                        status=status.HTTP_400_BAD_REQUEST)
    if target == 'organization':
        return Response({'success': False, 'error': 'انتشار سازمانی پس از دریافت تأیید Community Management API و پیاده‌سازی انتخاب صفحه فعال می‌شود.',
                         'code': 'ORG_REQUIRES_APPROVAL'},
                        status=status.HTTP_400_BAD_REQUEST)

    origin = _safe_frontend_origin(request.data.get('origin'), request)
    if not origin:
        return Response({'success': False, 'error': 'مبدأ رابط اتصال معتبر نیست', 'code': 'INVALID_ORIGIN'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not request.session.session_key:
        request.session.create()
    state = secrets.token_urlsafe(48)
    LinkedInOAuthState.objects.create(
        user=request.user,
        workspace_id=workspace_id,
        state_hash=_state_digest(state),
        session_key=request.session.session_key or '',
        platform_target=target,
        frontend_origin=origin,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    scope = 'openid profile email w_member_social'
    redirect_uri = _linkedin_redirect_uri(request)
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'state': state,
        'scope': scope,
    }
    auth_url = f'https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}'
    return Response({'success': True, 'data': {'authorization_url': auth_url}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def linkedin_config_status(request, workspace_id):
    """Expose setup health and exact callback URL to workspace members."""
    if not get_member(request.user, workspace_id):
        return Response({'success': False, 'error': 'فضای کاری یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)
    return Response({'success': True, 'data': _linkedin_configuration(request)})


@api_view(['GET'])
@permission_classes([AllowAny])
def linkedin_connect_callback(request):
    """OAuth callback for LinkedIn. This endpoint is public because LinkedIn redirects here."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description', '')

    if error:
        return _oauth_callback_html(False, f'خطای LinkedIn: {error_description}', 'linkedin')

    if not code or not state:
        return _oauth_callback_html(False, 'پارامترهای کافی ارسال نشده', 'linkedin')

    with transaction.atomic():
        oauth_state = LinkedInOAuthState.objects.select_for_update().filter(
            state_hash=_state_digest(state),
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).select_related('user').first()
        callback_session_key = request.session.session_key or ''
        if oauth_state and oauth_state.session_key != callback_session_key:
            oauth_state = None
        if oauth_state:
            oauth_state.consumed_at = timezone.now()
            oauth_state.save(update_fields=['consumed_at'])

    if not oauth_state:
        return _oauth_callback_html(False, 'SESSION_EXPIRED', 'linkedin')

    workspace_id = oauth_state.workspace_id
    user = oauth_state.user
    target = oauth_state.platform_target
    origin = oauth_state.frontend_origin

    if not WorkspaceMember.objects.filter(workspace_id=workspace_id, user=user, role='admin').exists():
        return _oauth_callback_html(False, 'دسترسی کاربر به فضای کاری معتبر نیست', 'linkedin', origin)

    client_id = getattr(settings, 'LINKEDIN_CLIENT_ID', '')
    client_secret = getattr(settings, 'LINKEDIN_CLIENT_SECRET', '')
    if not client_id or not client_secret:
        return _oauth_callback_html(False, 'تنظیمات LinkedIn کامل نیست', 'linkedin', origin)

    redirect_uri = _linkedin_redirect_uri(request)

    try:
        token_resp = requests.post(
            'https://www.linkedin.com/oauth/v2/accessToken',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
                'client_id': client_id,
                'client_secret': client_secret,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15,
        )
        token_data = token_resp.json()
        if not token_resp.ok or 'access_token' not in token_data:
            logger.warning('LinkedIn token exchange failed (status=%s)', token_resp.status_code)
            return _oauth_callback_html(False, 'دریافت توکن LinkedIn ناموفق بود', 'linkedin', origin)

        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token', '')
        expires_in = int(token_data.get('expires_in', 5184000))
        refresh_expires_in = token_data.get('refresh_token_expires_in')

        # Fetch userinfo to get URN
        userinfo_resp = requests.get(
            'https://api.linkedin.com/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=15,
        )
        if not userinfo_resp.ok:
            logger.warning('LinkedIn userinfo request failed (status=%s)', userinfo_resp.status_code)
            return _oauth_callback_html(False, 'دریافت اطلاعات حساب LinkedIn ناموفق بود', 'linkedin', origin)
        userinfo = userinfo_resp.json()
        sub = userinfo.get('sub', '')
        if not sub:
            return _oauth_callback_html(False, 'شناسه حساب LinkedIn دریافت نشد', 'linkedin', origin)
        person_urn = f'urn:li:person:{sub}' if sub else ''

        conn, _ = LinkedInConnection.objects.update_or_create(
            workspace_id=workspace_id,
            platform_target=target,
            defaults={
                'user': user,
                'linkedin_subject_id': sub,
                'access_token': encrypt_token(access_token),
                'refresh_token': encrypt_token(refresh_token) if refresh_token else '',
                'access_token_expires_at': timezone.now() + timedelta(seconds=expires_in),
                'refresh_token_expires_at': timezone.now() + timedelta(seconds=int(refresh_expires_in)) if refresh_expires_in else None,
                'person_urn': person_urn if target == 'personal' else '',
                'organization_urn': '',
                'name': userinfo.get('name', ''),
                'email': userinfo.get('email', ''),
                'avatar_url': userinfo.get('picture', ''),
                'scopes': str(token_data.get('scope', '')).split(),
                'status': 'active',
                'disconnected_at': None,
                'is_active': True,
            },
        )

        # Create or update the corresponding PublishChannel for the publish UI
        PublishChannel.objects.update_or_create(
            workspace_id=workspace_id,
            platform='linkedin',
            external_id=person_urn or f'linkedin-{conn.id}',
            defaults={
                'name': userinfo.get('name') or f'LinkedIn — {conn.get_platform_target_display()}',
                'channel_type': target,
                'is_verified': True,
                'is_active': True,
                'extra_data': {'connection_id': str(conn.id)},
            },
        )

        return _oauth_callback_html(True, 'اتصال LinkedIn با موفقیت انجام شد', 'linkedin', origin, {
            'connection_id': str(conn.id),
            'platform_target': target,
        })
    except requests.exceptions.RequestException:
        logger.exception('LinkedIn OAuth network request failed')
        return _oauth_callback_html(False, 'ارتباط با LinkedIn برقرار نشد؛ دوباره تلاش کنید', 'linkedin', origin)
    except Exception:
        logger.exception('LinkedIn OAuth callback failed')
        return _oauth_callback_html(False, 'اتصال LinkedIn با خطا مواجه شد', 'linkedin', origin)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def linkedin_disconnect(request, workspace_id, connection_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند اتصال حذف کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        conn = LinkedInConnection.objects.get(id=connection_id, workspace_id=workspace_id)
    except LinkedInConnection.DoesNotExist:
        return Response({'success': False, 'error': 'اتصال یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    conn.is_active = False
    conn.status = 'disconnected'
    conn.access_token = ''
    conn.refresh_token = ''
    conn.disconnected_at = timezone.now()
    conn.save(update_fields=['is_active', 'status', 'access_token', 'refresh_token', 'disconnected_at', 'updated_at'])

    linkedin_channels = PublishChannel.objects.filter(
        workspace_id=workspace_id, platform='linkedin', extra_data__connection_id=str(conn.id)
    )
    from publishing.models import PublishJob
    PublishJob.objects.filter(channel__in=linkedin_channels, status='queued').update(
        status='failed', completed_at=timezone.now(), next_retry_at=None,
    )
    linkedin_channels.update(is_active=False, is_verified=False)

    return Response({'success': True, 'data': {'message': 'اتصال LinkedIn حذف شد'}})


# ─────────────────────────────────────────────
# WordPress Application Passwords
# ─────────────────────────────────────────────

def _wordpress_authorize_url(site_url, app_name, app_id, success_url, reject_url):
    base = urljoin(site_url.rstrip('/') + '/', 'wp-admin/authorize-application.php')
    params = {
        'app_name': app_name,
        'app_id': app_id,
        'success_url': success_url,
    }
    if reject_url:
        params['reject_url'] = reject_url
    return f'{base}?{urlencode(params)}'


def _sync_wordpress_capabilities(connection):
    ok, error_type, result = wp_publisher.discover_capabilities(connection)
    if not ok:
        if error_type == 'auth_error':
            connection.status = 'invalid'
            connection.save(update_fields=['status'])
        return False, result
    connection.site_name = result['site_name']
    connection.capabilities = result['capabilities']
    connection.capabilities_synced_at = timezone.now()
    connection.status = 'active'
    connection.save(update_fields=['site_name', 'capabilities', 'capabilities_synced_at', 'status'])
    return True, result


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def wordpress_capabilities(request, workspace_id, channel_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)
    if request.method == 'POST' and member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند اطلاعات سایت را به‌روزرسانی کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)
    channel = PublishChannel.objects.filter(
        id=channel_id, workspace_id=workspace_id, platform='wordpress', is_active=True
    ).first()
    if not channel:
        return Response({'success': False, 'error': 'سایت وردپرس یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)
    connection_id = (channel.extra_data or {}).get('connection_id')
    connection = WordPressConnection.objects.filter(id=connection_id, workspace_id=workspace_id, is_active=True).first()
    if not connection:
        return Response({'success': False, 'error': 'اتصال وردپرس یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)
    if request.method == 'POST' or not connection.capabilities:
        ok, result = _sync_wordpress_capabilities(connection)
        if not ok:
            return Response({'success': False, 'error': result, 'code': 'WORDPRESS_SYNC_FAILED'},
                            status=status.HTTP_502_BAD_GATEWAY)
        channel.name = connection.site_name or channel.name
        channel.save(update_fields=['name'])
    return Response({'success': True, 'data': {
        'status': connection.status,
        'site_name': connection.site_name or channel.name,
        'site_url': connection.site_url,
        'capabilities': connection.capabilities or {},
        'synced_at': connection.capabilities_synced_at,
    }})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wordpress_connect_start(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند اتصال اضافه کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    raw_site_url = request.data.get('site_url', '').strip().rstrip('/')
    if not raw_site_url:
        return Response({'success': False, 'error': 'آدرس سایت وردپرس الزامی است', 'code': 'SITE_URL_REQUIRED'},
                        status=status.HTTP_400_BAD_REQUEST)

    site_url = normalize_site_url(raw_site_url)

    if not is_safe_url(site_url):
        return Response({'success': False, 'error': 'آدرس سایت نامعتبر یا غیرمجاز است', 'code': 'INVALID_SITE_URL'},
                        status=status.HTTP_400_BAD_REQUEST)

    ok, err = wp_publisher.check_application_passwords(site_url)
    if not ok:
        return Response({'success': False, 'error': err, 'code': 'UNSUPPORTED_SITE'},
                        status=status.HTTP_400_BAD_REQUEST)

    app_name = getattr(settings, 'WORDPRESS_APP_NAME', 'محتوایار')
    app_id = getattr(settings, 'WORDPRESS_APP_ID', '00000000-0000-0000-0000-000000000000')
    explicit_callback = getattr(settings, 'WORDPRESS_CALLBACK_URL', '')
    origin = request.data.get('origin', request.headers.get('Origin', '*'))

    state = sign_state({
        'workspace_id': str(workspace_id),
        'user_id': str(request.user.id),
        'site_url': site_url,
        'origin': origin,
    })

    if explicit_callback:
        success_url = f'{explicit_callback}?state={state}'
    else:
        success_url = f'https://localhost/api/workspaces/{workspace_id}/wordpress/callback/?state={state}'
    reject_url = success_url

    auth_url = _wordpress_authorize_url(site_url, app_name, app_id, success_url, reject_url)
    return Response({'success': True, 'data': {'authorization_url': auth_url, 'site_url': site_url, 'state': state}})


@api_view(['GET'])
@permission_classes([AllowAny])
def wordpress_connect_callback(request, workspace_id):
    """OAuth callback for WordPress. This endpoint is public because WordPress redirects here."""
    state = request.GET.get('state')
    username = request.GET.get('user_login', '').strip()
    password = request.GET.get('password', '').strip()

    if not state or not username or not password:
        return _oauth_callback_html(False, 'اطلاعات کامل بازگشت از وردپرس موجود نیست', 'wordpress')

    stored = unsign_state(state)
    if not stored:
        return _oauth_callback_html(False, 'SESSION_EXPIRED', 'wordpress')

    if str(stored.get('workspace_id')) != str(workspace_id):
        return _oauth_callback_html(False, 'WORKSPACE_MISMATCH', 'wordpress')

    site_url = stored.get('site_url', '')
    user_id = stored.get('user_id')
    origin = stored.get('origin', '*')

    if not site_url or not is_safe_url(site_url):
        return _oauth_callback_html(False, 'SITE_URL_MISSING', 'wordpress', origin)

    from users.models import User
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return _oauth_callback_html(False, 'کاربر مرتبط با این درخواست یافت نشد', 'wordpress', origin)

    try:
        conn, _ = WordPressConnection.objects.update_or_create(
            workspace_id=workspace_id,
            user=user,
            site_url=site_url,
            defaults={
                'wp_username': username,
                'application_password': encrypt_token(password),
                'status': 'active',
                'is_active': True,
            },
        )

        if not wp_publisher.validate_credentials(conn):
            conn.status = 'invalid'
            conn.save(update_fields=['status'])
            return _oauth_callback_html(False, 'اعتبارنامه وردپرس معتبر نیست', 'wordpress', origin)

        _sync_wordpress_capabilities(conn)

        PublishChannel.objects.update_or_create(
            workspace_id=workspace_id,
            platform='wordpress',
            external_id=site_url,
            defaults={
                'name': conn.site_name or f'WordPress — {conn.site_url}',
                'channel_type': 'site',
                'is_verified': True,
                'is_active': True,
                'extra_data': {'connection_id': str(conn.id)},
            },
        )

        return _oauth_callback_html(True, 'اتصال WordPress با موفقیت انجام شد', 'wordpress', origin, {
            'connection_id': str(conn.id),
            'site_url': site_url,
        })
    except Exception as e:
        logger.exception(f'WordPress OAuth callback failed: {e}')
        return _oauth_callback_html(False, 'اتصال WordPress با خطا مواجه شد', 'wordpress', origin)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def wordpress_disconnect(request, workspace_id, connection_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند اتصال حذف کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        conn = WordPressConnection.objects.get(id=connection_id, workspace_id=workspace_id)
    except WordPressConnection.DoesNotExist:
        return Response({'success': False, 'error': 'اتصال یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    conn.is_active = False
    conn.status = 'disconnected'
    conn.save(update_fields=['is_active', 'status'])

    PublishChannel.objects.filter(workspace_id=workspace_id, platform='wordpress', external_id=conn.site_url).update(
        is_active=False, is_verified=False
    )

    return Response({'success': True, 'data': {'message': 'اتصال WordPress حذف شد. برای امنیت کامل، رمز اپلیکیشن را از پروفایل وردپرس خود نیز لغو کنید.'}})
