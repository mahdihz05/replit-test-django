from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember
from .models import Wallet, WalletTransaction
from .serializers import WalletSerializer, WalletTransactionSerializer


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_detail(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        wallet = Wallet.objects.get(workspace_id=workspace_id)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(workspace_id=workspace_id)

    recent_tx = WalletTransaction.objects.filter(wallet=wallet)[:5]
    return Response({
        'success': True,
        'data': {
            **WalletSerializer(wallet).data,
            'recent_transactions': WalletTransactionSerializer(recent_tx, many=True).data
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_list(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        wallet = Wallet.objects.get(workspace_id=workspace_id)
    except Wallet.DoesNotExist:
        return Response({'success': True, 'data': []})

    transactions = WalletTransaction.objects.filter(wallet=wallet)
    return Response({'success': True, 'data': WalletTransactionSerializer(transactions, many=True).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def charge_wallet(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member or member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند کیف پول را شارژ کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    amount = request.data.get('amount')
    if not amount or float(amount) <= 0:
        return Response({'success': False, 'error': 'مبلغ نامعتبر است', 'code': 'INVALID_AMOUNT'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        wallet = Wallet.objects.get(workspace_id=workspace_id)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(workspace_id=workspace_id)

    wallet.balance += float(amount)
    wallet.save()

    WalletTransaction.objects.create(
        wallet=wallet,
        type='charge',
        amount=amount,
        description=request.data.get('description', 'شارژ دستی کیف پول')
    )

    return Response({'success': True, 'data': WalletSerializer(wallet).data})
