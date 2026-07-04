import logging
import os
import uuid
import mimetypes
from datetime import timedelta
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember
from channels_app.models import PublishChannel
from .models import PublishJob, PublishLog, PublishAttachment
from .serializers import PublishJobSerializer, PublishAttachmentSerializer

logger = logging.getLogger(__name__)


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


# Media size limits per platform (bytes). Based on public docs / bot API limits.
PLATFORM_MEDIA_LIMITS = {
    'telegram': 50 * 1024 * 1024,
    'bale': 50 * 1024 * 1024,
    'linkedin': 5 * 1024 * 1024 * 1024,  # video upload limit ~5GB (phase upload)
    'wordpress': None,  # checked per site later
}

MEDIA_TYPE_TO_PLATFORM = {
    'image': {'telegram', 'bale', 'linkedin', 'wordpress'},
    'video': {'telegram', 'bale', 'linkedin', 'wordpress'},
    'voice': {'telegram', 'bale', 'wordpress'},
    'document': {'telegram', 'bale', 'linkedin', 'wordpress'},
}

PLATFORM_TO_MEDIA_TYPES = {
    'telegram': {'image', 'video', 'voice', 'document'},
    'bale': {'image', 'video', 'voice', 'document'},
    'linkedin': {'image', 'video', 'document'},
    'wordpress': {'image', 'video', 'voice', 'document'},
    'website': set(),
}


def _attachment_from_id(attachment_id, workspace_id):
    try:
        from .models import PublishAttachment
        return PublishAttachment.objects.get(id=attachment_id, workspace_id=workspace_id, is_active=True)
    except Exception:
        return None


def _validate_attachments(attachments, channel_ids, workspace_id):
    """Return (validated_list, error_response). attachments is a list of dicts with id, media_type."""
    if not attachments:
        return [], None
    from .models import PublishAttachment
    from channels_app.models import PublishChannel

    ids = [a.get('id') for a in attachments if a.get('id')]
    objs = {str(a.id): a for a in PublishAttachment.objects.filter(id__in=ids, workspace_id=workspace_id, is_active=True)}

    validated = []
    unknown_ids = []
    for att in attachments:
        obj = objs.get(str(att.get('id')))
        if not obj:
            unknown_ids.append(str(att.get('id')))
            continue
        media_type = att.get('media_type') or obj.media_type
        if media_type not in MEDIA_TYPE_TO_PLATFORM:
            continue
        validated.append({
            'id': str(obj.id),
            'media_type': media_type,
            'file_path': obj.file_path,
            'mime_type': obj.mime_type,
            'file_size_bytes': obj.file_size_bytes or 0,
            'original_filename': obj.original_filename,
            'object': obj,
        })

    if unknown_ids:
        return None, Response(
            {'success': False, 'error': f'برخی ضمیمه‌ها یافت نشدند یا متعلق به این فضای کاری نیستند: {", ".join(unknown_ids[:3])}', 'code': 'INVALID_ATTACHMENTS'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not validated:
        return [], None

    channels = list(PublishChannel.objects.filter(id__in=channel_ids, is_active=True, is_verified=True))
    smallest_limit = None
    for ch in channels:
        limit = PLATFORM_MEDIA_LIMITS.get(ch.platform)
        if limit is not None and (smallest_limit is None or limit < smallest_limit):
            smallest_limit = limit

    if smallest_limit is not None:
        for v in validated:
            if v['file_size_bytes'] > smallest_limit:
                return None, Response(
                    {'success': False, 'error': f'حجم فایل بیش از حد مجاز است. کوچک‌ترین محدودیت انتخاب‌شده: {smallest_limit // (1024 * 1024)} مگابایت', 'code': 'FILE_TOO_LARGE'},
                    status=status.HTTP_400_BAD_REQUEST
                )
    return validated, None


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


def _publish_to_channel(channel, title, body, content_obj, attachments=None):
    """Immediately publish text/media to a channel. Returns (success, error_msg, platform_msg_id)"""
    from content.models import Content
    if content_obj is None:
        # create a temporary content for the publishers
        content_obj = Content(title=title, body=body)

    if channel.platform == 'telegram':
        from .publishers import telegram as tg_pub
        return tg_pub.publish(channel, content_obj, attachments=attachments)
    elif channel.platform == 'bale':
        from .publishers import bale as bale_pub
        return bale_pub.publish(channel, content_obj, attachments=attachments)
    elif channel.platform == 'website':
        from .publishers import website as ws_pub
        return ws_pub.publish(channel, content_obj, attachments=attachments)
    elif channel.platform == 'linkedin':
        from .publishers import linkedin as li_pub
        return li_pub.publish(channel, content_obj, attachments=attachments)
    elif channel.platform == 'wordpress':
        from .publishers import wordpress as wp_pub
        return wp_pub.publish(channel, content_obj, attachments=attachments)

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
    attachments = request.data.get('attachments', [])

    if not channel_ids:
        return Response({'success': False, 'error': 'حداقل یک کانال انتخاب کنید', 'code': 'NO_CHANNELS'},
                        status=status.HTTP_400_BAD_REQUEST)

    validated_attachments, err = _validate_attachments(attachments, channel_ids, workspace_id)
    if err:
        return err

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

        ch_attachments = _filter_attachments_for_channel(channel.platform, validated_attachments)
        success, error_type, msg_id_or_err = _publish_to_channel(channel, title, body, content_obj, ch_attachments)

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


def _filter_attachments_for_channel(platform, attachments):
    """Return only attachments supported by the platform."""
    if not attachments:
        return []
    supported = PLATFORM_TO_MEDIA_TYPES.get(platform, set())
    return [a for a in attachments if a['media_type'] in supported]


def _record_job(content_obj, channel, job_status, error_msg, attachments=None):
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
        if attachments:
            job.attachments.set([a['object'] for a in attachments if a.get('object')])
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
    attachments = request.data.get('attachments', [])

    if not channel_ids:
        return Response({'success': False, 'error': 'حداقل یک کانال انتخاب کنید', 'code': 'NO_CHANNELS'},
                        status=status.HTTP_400_BAD_REQUEST)

    validated_attachments, err = _validate_attachments(attachments, channel_ids, workspace_id)
    if err:
        return err

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
        if validated_attachments:
            ch_attachments = _filter_attachments_for_channel(channel.platform, validated_attachments)
            job.attachments.set([a['object'] for a in ch_attachments if a.get('object')])
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_attachment(request, workspace_id):
    """Upload a file and create a PublishAttachment record."""
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import os, uuid, mimetypes

    file = request.FILES.get('file')
    if not file:
        return Response({'success': False, 'error': 'فایل الزامی است', 'code': 'MISSING_FILE'},
                        status=status.HTTP_400_BAD_REQUEST)

    media_type = request.data.get('media_type') or _guess_media_type(file.name)
    allowed_types = {'image', 'video', 'voice', 'document'}
    if media_type not in allowed_types:
        media_type = 'document'

    ext = os.path.splitext(file.name)[1]
    filename = f'{uuid.uuid4()}{ext}'
    path = os.path.join('publish_attachments', filename)
    full_path = default_storage.save(path, ContentFile(file.read()))
    file_size = default_storage.size(full_path)
    mime_type = file.content_type or mimetypes.guess_type(file.name)[0] or 'application/octet-stream'

    attachment = PublishAttachment.objects.create(
        workspace_id=workspace_id,
        file_path=full_path,
        media_type=media_type,
        mime_type=mime_type,
        file_size_bytes=file_size,
        original_filename=file.name,
    )

    return Response({'success': True, 'data': PublishAttachmentSerializer(attachment).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_attachment_from_content_image(request, workspace_id):
    """Create a PublishAttachment from an existing Content image."""
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    from content.models import Content
    content_id = request.data.get('content_id')
    try:
        content = Content.objects.get(id=content_id, workspace_id=workspace_id, is_active=True)
    except Content.DoesNotExist:
        return Response({'success': False, 'error': 'محتوا یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    if not content.image:
        return Response({'success': False, 'error': 'این محتوا تصویر ندارد', 'code': 'NO_IMAGE'},
                        status=status.HTTP_400_BAD_REQUEST)

    import os, mimetypes
    attachment = PublishAttachment.objects.create(
        workspace_id=workspace_id,
        content=content,
        file_path=content.image.name,
        media_type='image',
        mime_type=mimetypes.guess_type(content.image.name)[0] or 'image/png',
        file_size_bytes=content.image.size if hasattr(content.image, 'size') else 0,
        original_filename=os.path.basename(content.image.name),
    )

    return Response({'success': True, 'data': PublishAttachmentSerializer(attachment).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_attachments(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    qs = PublishAttachment.objects.filter(workspace_id=workspace_id, is_active=True)
    content_id = request.query_params.get('content_id')
    if content_id:
        qs = qs.filter(content_id=content_id)
    return Response({'success': True, 'data': PublishAttachmentSerializer(qs, many=True).data})


def _guess_media_type(filename):
    ext = os.path.splitext(filename.lower())[1]
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'):
        return 'image'
    if ext in ('.mp4', '.mov', '.avi', '.mkv', '.webm'):
        return 'video'
    if ext in ('.mp3', '.ogg', '.wav', '.m4a', '.aac'):
        return 'voice'
    return 'document'
