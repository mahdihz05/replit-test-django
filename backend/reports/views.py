from django.db.models import Count, Sum
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

    return Response({'success': True, 'data': {
        'total': total,
        'by_status': {item['status']: item['count'] for item in by_status},
        'recent': contents.order_by('-created_at').values('id', 'title', 'status', 'created_at')[:5]
    }})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def publishing_report(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    from publishing.models import PublishJob
    jobs = PublishJob.objects.filter(content__workspace_id=workspace_id)
    by_status = jobs.values('status').annotate(count=Count('id'))
    by_channel = jobs.values('channel__name', 'channel__platform').annotate(count=Count('id'))

    return Response({'success': True, 'data': {
        'total': jobs.count(),
        'by_status': {item['status']: item['count'] for item in by_status},
        'by_channel': list(by_channel),
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

    return Response({'success': True, 'data': {
        'total_spent': float(total_spent),
        'transaction_count': tx_count,
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

    return Response({'success': True, 'data': {
        'total_errors': logs.count(),
        'by_type': {item['error_type']: item['count'] for item in by_type},
        'recent': list(logs.values('error_type', 'user_message', 'attempted_at')[:10])
    }})
