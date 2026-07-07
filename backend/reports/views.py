from datetime import timedelta

import jdatetime
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


def _last_6_persian_months():
    """Return the last 6 Persian months with labels and Gregorian date boundaries."""
    today = jdatetime.date.today()
    months = []
    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            year -= 1
            month += 12

        start = jdatetime.date(year, month, 1)
        if month == 12:
            end = jdatetime.date(year + 1, 1, 1)
        else:
            end = jdatetime.date(year, month + 1, 1)

        months.append({
            'label': start.strftime('%B %Y'),
            'start_gregorian': start.togregorian(),
            'end_gregorian': end.togregorian(),
        })
    return months


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    from content.models import Content
    from publishing.models import PublishJob, PublishLog
    from channels_app.models import PublishChannel
    from wallet.models import Wallet, WalletTransaction

    contents = Content.objects.filter(workspace_id=workspace_id, is_active=True)
    content_status = contents.values('status').annotate(count=Count('id'))

    jobs = PublishJob.objects.filter(content__workspace_id=workspace_id)
    job_status = jobs.values('status').annotate(count=Count('id'))

    today = timezone.now().date()
    publishes_by_day = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        # Use completed_at for successful publishes so scheduled/retried jobs
        # are counted on the day they actually finished, not when they were queued.
        publishes_by_day.append({
            'date': d.strftime('%m/%d'),
            'count': jobs.filter(completed_at__date=d, status='success').count()
        })

    channels = PublishChannel.objects.filter(workspace_id=workspace_id, is_active=True)
    channel_platform = channels.values('platform').annotate(count=Count('id'))
    verified_count = channels.filter(is_verified=True).count()

    try:
        wallet = Wallet.objects.get(workspace_id=workspace_id)
        balance = float(wallet.balance)
        total_spent = WalletTransaction.objects.filter(wallet=wallet, type='deduct').aggregate(
            total=Sum('amount'))['total'] or 0
        total_charged = WalletTransaction.objects.filter(wallet=wallet, type='charge').aggregate(
            total=Sum('amount'))['total'] or 0
    except Wallet.DoesNotExist:
        balance = 0
        total_spent = 0
        total_charged = 0

    recent_errors = PublishLog.objects.filter(
        job__content__workspace_id=workspace_id, success=False
    ).order_by('-attempted_at').values('error_type', 'user_message', 'attempted_at')[:5]

    return Response({'success': True, 'data': {
        'contents': {
            'total': contents.count(),
            'by_status': {item['status']: item['count'] for item in content_status},
        },
        'publishes': {
            'total': jobs.count(),
            'by_status': {item['status']: item['count'] for item in job_status},
            'by_day': publishes_by_day,
        },
        'channels': {
            'total': channels.count(),
            'verified': verified_count,
            'by_platform': {item['platform']: item['count'] for item in channel_platform},
        },
        'wallet': {
            'balance': balance,
            'total_spent': float(total_spent),
            'total_charged': float(total_charged),
        },
        'recent_errors': list(recent_errors),
    }})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def content_report(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    from content.models import Content
    contents = Content.objects.filter(workspace_id=workspace_id, is_active=True)
    by_status = contents.values('status').annotate(count=Count('id'))
    total = contents.count()

    # Last 6 Persian months of content creation (true month boundaries)
    by_month = []
    for m in _last_6_persian_months():
        count = contents.filter(
            created_at__date__gte=m['start_gregorian'],
            created_at__date__lt=m['end_gregorian']
        ).count()
        by_month.append({'label': m['label'], 'count': count})

    return Response({'success': True, 'data': {
        'total': total,
        'by_status': {item['status']: item['count'] for item in by_status},
        'by_month': by_month,
        'recent': list(contents.order_by('-created_at').values('id', 'title', 'status', 'created_at')[:5])
    }})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def publishing_report(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    from publishing.models import PublishJob
    from channels_app.models import PublishChannel

    jobs = PublishJob.objects.filter(content__workspace_id=workspace_id)
    by_status = jobs.values('status').annotate(count=Count('id'))
    by_channel = jobs.values('channel__name', 'channel__platform').annotate(count=Count('id'))

    # 30-day publish trend by completion date (successful publishes)
    today = timezone.now().date()
    by_day = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        by_day.append({
            'date': d.strftime('%m/%d'),
            'count': jobs.filter(completed_at__date=d, status='success').count()
        })

    # Publishes by platform (via channel)
    by_platform = {}
    for item in jobs.values('channel__platform').annotate(count=Count('id')):
        by_platform[item['channel__platform']] = item['count']

    total_channels = PublishChannel.objects.filter(workspace_id=workspace_id, is_active=True).count()

    return Response({'success': True, 'data': {
        'total': jobs.count(),
        'by_status': {item['status']: item['count'] for item in by_status},
        'by_channel': list(by_channel),
        'by_day': by_day,
        'by_platform': by_platform,
        'total_channels': total_channels,
    }})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_usage_report(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    from wallet.models import WalletTransaction, Wallet
    try:
        wallet = Wallet.objects.get(workspace_id=workspace_id)
        ai_deductions = WalletTransaction.objects.filter(wallet=wallet, type='deduct')
        total_spent = ai_deductions.aggregate(total=Sum('amount'))['total'] or 0
        tx_count = ai_deductions.count()
    except Wallet.DoesNotExist:
        total_spent = 0
        tx_count = 0
        ai_deductions = WalletTransaction.objects.none()

    # 30-day AI spending trend
    today = timezone.now().date()
    by_day = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        by_day.append({
            'date': d.strftime('%m/%d'),
            'amount': float(ai_deductions.filter(created_at__date=d).aggregate(
                total=Sum('amount'))['total'] or 0),
        })

    return Response({'success': True, 'data': {
        'total_spent': float(total_spent),
        'transaction_count': tx_count,
        'by_day': by_day,
    }})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def errors_report(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    from publishing.models import PublishLog
    logs = PublishLog.objects.filter(job__content__workspace_id=workspace_id, success=False)
    by_type = logs.values('error_type').annotate(count=Count('id'))

    # 30-day error trend
    today = timezone.now().date()
    by_day = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        by_day.append({
            'date': d.strftime('%m/%d'),
            'count': logs.filter(attempted_at__date=d).count()
        })

    return Response({'success': True, 'data': {
        'total_errors': logs.count(),
        'by_type': {item['error_type']: item['count'] for item in by_type},
        'by_day': by_day,
        'recent': list(logs.values('error_type', 'user_message', 'attempted_at')[:10])
    }})
