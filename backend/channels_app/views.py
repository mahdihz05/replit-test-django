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
    return Response({'success': True, 'data': PublishChannelSerializer(channels, many=True).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_start(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند کانال اضافه کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    platform = request.data.get('platform', 'telegram')
    if platform not in ['telegram', 'bale']:
        return Response({'success': False, 'error': 'پلتفرم نامعتبر است', 'code': 'INVALID_PLATFORM'},
                        status=status.HTTP_400_BAD_REQUEST)

    token = ChannelVerification.generate_token()
    while ChannelVerification.objects.filter(token=token).exists():
        token = ChannelVerification.generate_token()

    verification = ChannelVerification.objects.create(
        workspace_id=workspace_id,
        requested_by=request.user,
        platform=platform,
        token=token,
        expires_at=timezone.now() + timedelta(minutes=15)
    )
    return Response({'success': True, 'data': ChannelVerificationSerializer(verification).data},
                    status=status.HTTP_201_CREATED)


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
