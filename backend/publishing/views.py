import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember
from channels_app.models import PublishChannel
from .models import PublishJob, PublishLog
from .serializers import PublishJobSerializer

logger = logging.getLogger(__name__)


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


def _get_text(content_id, custom_text, workspace_id):
    """Return (title, body, content_obj, error_response)"""
    if content_id:
        try:
            from content.models import Content
            content = Content.objects.get(id=content_id, workspace_id=workspace_id)
            return content.title or '', content.body or '', content, None
        except Exception:
            return None, None, None, Response(
                {'success': False, 'error': 'محتوا یافت نشد', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
    if custom_text:
        return 'انتشار مستقیم', custom_text, None, None
    return None, None, None, Response(
        {'success': False, 'error': 'متن یا محتوا الزامی است', 'code': 'MISSING_TEXT'},
        status=status.HTTP_400_BAD_REQUEST
    )


def _publish_to_channel(channel, title, body, content_obj):
    """Immediately publish text to a channel. Returns (success, error_msg, platform_msg_id)"""
    from content.models import Content
    if content_obj is None:
        # create a temporary content for the publishers
        content_obj = Content(title=title, body=body)

    if channel.platform == 'telegram':
        from .publishers import telegram as tg_pub
        return tg_pub.publish(channel, content_obj)
    elif channel.platform == 'bale':
        from .publishers import bale as bale_pub
        return bale_pub.publish(channel, content_obj)
    elif channel.platform == 'website':
        from .publishers import website as ws_pub
        return ws_pub.publish(channel, content_obj)
    elif channel.platform == 'linkedin':
        from .publishers import linkedin as li_pub
        return li_pub.publish(channel, content_obj)
    elif channel.platform == 'wordpress':
        from .publishers import wordpress as wp_pub
        return wp_pub.publish(channel, content_obj)

    return False, 'پلتفرم پشتیبانی نمی‌شود', None


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_now(request, workspace_id):
    """Immediately publish to one or more channels."""
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    content_id = request.data.get('content_id')
    custom_text = request.data.get('custom_text', '').strip()
    channel_ids = request.data.get('channel_ids', [])

    if not channel_ids:
        return Response({'success': False, 'error': 'حداقل یک کانال انتخاب کنید', 'code': 'NO_CHANNELS'},
                        status=status.HTTP_400_BAD_REQUEST)

    title, body, content_obj, err = _get_text(content_id, custom_text, workspace_id)
    if err:
        return err

    results = []
    all_success = True
    any_success = False

    for ch_id in channel_ids:
        try:
            channel = PublishChannel.objects.get(id=ch_id, workspace_id=workspace_id, is_active=True, is_verified=True)
        except PublishChannel.DoesNotExist:
            results.append({
                'channel_id': str(ch_id),
                'channel_name': '—',
                'status': 'failed',
                'error': 'کانال یافت نشد یا تأیید نشده است'
            })
            all_success = False
            continue

        success, error_type, msg_id_or_err = _publish_to_channel(channel, title, body, content_obj)

        if success:
            any_success = True
            results.append({
                'channel_id': str(channel.id),
                'channel_name': channel.name,
                'platform': channel.platform,
                'status': 'success',
                'message_id': str(msg_id_or_err) if msg_id_or_err else None,
            })
            # Log to PublishJob if linked to a content model
            if content_obj and hasattr(content_obj, 'pk') and content_obj.pk:
                _record_job(content_obj, channel, 'success', None)
        else:
            all_success = False
            error_msg = msg_id_or_err or 'خطای ناشناخته'
            results.append({
                'channel_id': str(channel.id),
                'channel_name': channel.name,
                'platform': channel.platform,
                'status': 'failed',
                'error': error_msg,
            })
            if content_obj and hasattr(content_obj, 'pk') and content_obj.pk:
                _record_job(content_obj, channel, 'failed', error_msg)

    overall = 'published' if all_success else ('partial' if any_success else 'failed')
    return Response({'success': True, 'data': {
        'overall_status': overall,
        'results': results
    }})


def _record_job(content_obj, channel, job_status, error_msg):
    """Create a PublishJob + PublishLog record for tracking."""
    try:
        job = PublishJob.objects.create(
            content=content_obj,
            channel=channel,
            status='success' if job_status == 'success' else 'failed',
            started_at=timezone.now(),
            completed_at=timezone.now(),
            attempt_count=1,
        )
        PublishLog.objects.create(
            job=job,
            attempt_number=1,
            success=(job_status == 'success'),
            error_message=error_msg or '',
            user_message=error_msg or '',
        )
    except Exception as e:
        logger.warning(f'Failed to record publish job: {e}')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_schedule(request, workspace_id):
    """Schedule a publish job for a future time."""
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    content_id = request.data.get('content_id')
    custom_text = request.data.get('custom_text', '').strip()
    channel_ids = request.data.get('channel_ids', [])
    scheduled_at_str = request.data.get('scheduled_at')

    if not channel_ids:
        return Response({'success': False, 'error': 'حداقل یک کانال انتخاب کنید', 'code': 'NO_CHANNELS'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not scheduled_at_str:
        return Response({'success': False, 'error': 'زمان انتشار الزامی است', 'code': 'NO_SCHEDULE_TIME'},
                        status=status.HTTP_400_BAD_REQUEST)

    from django.utils.dateparse import parse_datetime
    scheduled_at = parse_datetime(scheduled_at_str)
    if not scheduled_at:
        return Response({'success': False, 'error': 'فرمت زمان نامعتبر است', 'code': 'INVALID_TIME'},
                        status=status.HTTP_400_BAD_REQUEST)

    if scheduled_at <= timezone.now():
        return Response({'success': False, 'error': 'زمان انتشار باید در آینده باشد', 'code': 'PAST_TIME'},
                        status=status.HTTP_400_BAD_REQUEST)

    title, body, content_obj, err = _get_text(content_id, custom_text, workspace_id)
    if err:
        return err

    if content_obj is None:
        # For scheduled jobs, we need a real content object
        from content.models import Content
        content_obj = Content.objects.create(
            workspace_id=workspace_id,
            created_by=request.user,
            title='زمان‌بندی مستقیم',
            body=body,
            status='draft',
        )

    created_jobs = []
    for ch_id in channel_ids:
        try:
            channel = PublishChannel.objects.get(id=ch_id, workspace_id=workspace_id, is_active=True, is_verified=True)
        except PublishChannel.DoesNotExist:
            continue

        job = PublishJob.objects.create(
            content=content_obj,
            channel=channel,
            status='queued',
            scheduled_at=scheduled_at,
        )
        created_jobs.append({'job_id': str(job.id), 'channel_name': channel.name})

    return Response({'success': True, 'data': {
        'scheduled_at': scheduled_at.isoformat(),
        'jobs': created_jobs
    }})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_job(request, workspace_id, job_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        job = PublishJob.objects.get(id=job_id, content__workspace_id=workspace_id, status='queued')
    except PublishJob.DoesNotExist:
        return Response({'success': False, 'error': 'کار یافت نشد یا قابل لغو نیست', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    job.status = 'failed'
    job.save()
    return Response({'success': True, 'data': {'message': 'کار لغو شد'}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def publish_history(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    jobs = PublishJob.objects.filter(
        content__workspace_id=workspace_id
    ).select_related('content', 'channel').prefetch_related('logs').order_by('-created_at')[:50]

    return Response({'success': True, 'data': PublishJobSerializer(jobs, many=True).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def publish_queue(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    jobs = PublishJob.objects.filter(
        content__workspace_id=workspace_id,
        status='queued',
        scheduled_at__isnull=False,
    ).select_related('content', 'channel').order_by('scheduled_at')

    return Response({'success': True, 'data': PublishJobSerializer(jobs, many=True).data})
