from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember
from .models import PublishJob
from .serializers import PublishJobSerializer


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_list(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    jobs = PublishJob.objects.filter(
        content__workspace_id=workspace_id
    ).select_related('content', 'channel').prefetch_related('logs')

    return Response({'success': True, 'data': PublishJobSerializer(jobs, many=True).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_detail(request, workspace_id, job_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        job = PublishJob.objects.get(id=job_id, content__workspace_id=workspace_id)
    except PublishJob.DoesNotExist:
        return Response({'success': False, 'error': 'کار یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    return Response({'success': True, 'data': PublishJobSerializer(job).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def job_retry(request, workspace_id, job_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        job = PublishJob.objects.get(id=job_id, content__workspace_id=workspace_id, status='failed')
    except PublishJob.DoesNotExist:
        return Response({'success': False, 'error': 'کار یافت نشد یا قابل تلاش مجدد نیست', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    job.status = 'queued'
    job.attempt_count = 0
    job.next_retry_at = None
    job.save()

    return Response({'success': True, 'data': {'message': 'کار مجدداً در صف قرار گرفت'}})
