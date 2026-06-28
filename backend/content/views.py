from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember, Workspace
from .models import Content, ContentVersion
from .serializers import ContentSerializer, ContentVersionSerializer


def get_workspace_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def content_list(request, workspace_id):
    member = get_workspace_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        qs = Content.objects.filter(workspace_id=workspace_id, is_active=True)
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        tags = request.query_params.get('tags')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(body__icontains=search))
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                qs = qs.filter(tags__contains=tag.strip())

        return Response({'success': True, 'data': ContentSerializer(qs, many=True, context={'request': request}).data})

    serializer = ContentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'error': str(serializer.errors), 'code': 'VALIDATION_ERROR'},
                        status=status.HTTP_400_BAD_REQUEST)

    content = serializer.save(workspace_id=workspace_id, created_by=request.user)
    if content.body:
        ContentVersion.objects.create(
            content=content,
            body=content.body,
            version_number=1,
            source='user'
        )
    return Response({'success': True, 'data': ContentSerializer(content, context={'request': request}).data},
                    status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def content_detail(request, workspace_id, content_id):
    member = get_workspace_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        content = Content.objects.get(id=content_id, workspace_id=workspace_id, is_active=True)
    except Content.DoesNotExist:
        return Response({'success': False, 'error': 'محتوا یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({'success': True, 'data': ContentSerializer(content, context={'request': request}).data})

    if request.method == 'DELETE':
        if member.role != 'admin':
            return Response({'success': False, 'error': 'فقط ادمین می‌تواند محتوا حذف کند', 'code': 'FORBIDDEN'},
                            status=status.HTTP_403_FORBIDDEN)
        content.is_active = False
        content.save()
        return Response({'success': True, 'data': {'message': 'محتوا حذف شد'}})

    old_body = content.body
    serializer = ContentSerializer(content, data=request.data, partial=True, context={'request': request})
    if not serializer.is_valid():
        return Response({'success': False, 'error': str(serializer.errors), 'code': 'VALIDATION_ERROR'},
                        status=status.HTTP_400_BAD_REQUEST)
    content = serializer.save()

    if content.body and content.body != old_body:
        last_version = ContentVersion.objects.filter(content=content).order_by('-version_number').first()
        version_number = (last_version.version_number + 1) if last_version else 1
        ContentVersion.objects.create(
            content=content,
            body=content.body,
            version_number=version_number,
            source='user'
        )

    return Response({'success': True, 'data': ContentSerializer(content, context={'request': request}).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def content_versions(request, workspace_id, content_id):
    member = get_workspace_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        content = Content.objects.get(id=content_id, workspace_id=workspace_id, is_active=True)
    except Content.DoesNotExist:
        return Response({'success': False, 'error': 'محتوا یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    versions = ContentVersion.objects.filter(content=content)
    return Response({'success': True, 'data': ContentVersionSerializer(versions, many=True).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_content(request, workspace_id, content_id):
    member = get_workspace_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        content = Content.objects.get(id=content_id, workspace_id=workspace_id, is_active=True)
    except Content.DoesNotExist:
        return Response({'success': False, 'error': 'محتوا یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    channel_ids = request.data.get('channel_ids', [])
    scheduled_at = request.data.get('scheduled_at')

    if not channel_ids:
        return Response({'success': False, 'error': 'حداقل یک کانال انتخاب کنید', 'code': 'NO_CHANNELS'},
                        status=status.HTTP_400_BAD_REQUEST)

    from channels_app.models import PublishChannel
    from publishing.models import PublishJob

    jobs = []
    for channel_id in channel_ids:
        try:
            channel = PublishChannel.objects.get(id=channel_id, workspace_id=workspace_id, is_active=True)
        except PublishChannel.DoesNotExist:
            continue
        job = PublishJob.objects.create(
            content=content,
            channel=channel,
            scheduled_at=scheduled_at
        )
        jobs.append(str(job.id))

    if scheduled_at:
        content.status = 'scheduled'
        content.scheduled_at = scheduled_at
    else:
        content.status = 'publishing'
    content.save()

    return Response({'success': True, 'data': {'job_ids': jobs, 'message': 'عملیات انتشار شروع شد'}})
