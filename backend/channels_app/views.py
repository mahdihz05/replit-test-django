from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember
from .models import PublishChannel, ChannelVerification
from .serializers import PublishChannelSerializer, ChannelVerificationSerializer


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


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


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def channel_detail(request, workspace_id, channel_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند کانال حذف کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        channel = PublishChannel.objects.get(id=channel_id, workspace_id=workspace_id)
    except PublishChannel.DoesNotExist:
        return Response({'success': False, 'error': 'کانال یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

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
    except PublishChannel.DoesNotExist:
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
    else:
        return Response({'success': False, 'error': 'این پلتفرم از تست پشتیبانی نمی‌کند', 'code': 'UNSUPPORTED'},
                        status=status.HTTP_400_BAD_REQUEST)

    if err:
        return Response({'success': False, 'error': err, 'code': 'SEND_FAILED'},
                        status=status.HTTP_502_BAD_GATEWAY)

    return Response({'success': True, 'data': {'message': 'پیام آزمایشی با موفقیت ارسال شد'}})
