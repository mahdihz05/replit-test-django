from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Workspace, WorkspaceMember
from .serializers import (
    WorkspaceSerializer, WorkspaceMemberSerializer, AddMemberSerializer
)
from .permissions import IsWorkspaceMember, IsWorkspaceAdmin


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def workspace_list(request):
    if request.method == 'GET':
        member_ws_ids = WorkspaceMember.objects.filter(
            user=request.user
        ).values_list('workspace_id', flat=True)
        owned = Workspace.objects.filter(owner=request.user, is_active=True)
        member = Workspace.objects.filter(id__in=member_ws_ids, is_active=True)
        workspaces = (owned | member).distinct()
        return Response({'success': True, 'data': WorkspaceSerializer(workspaces, many=True).data})

    serializer = WorkspaceSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'error': str(serializer.errors), 'code': 'VALIDATION_ERROR'},
                        status=status.HTTP_400_BAD_REQUEST)

    workspace = serializer.save(owner=request.user)
    WorkspaceMember.objects.create(
        workspace=workspace,
        user=request.user,
        role='admin',
        added_by=request.user
    )
    from wallet.models import Wallet
    Wallet.objects.create(workspace=workspace)
    return Response({'success': True, 'data': WorkspaceSerializer(workspace).data},
                    status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def workspace_detail(request, workspace_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id, is_active=True)
    except Workspace.DoesNotExist:
        return Response({'success': False, 'error': 'فضای کاری یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    member = WorkspaceMember.objects.filter(workspace=workspace, user=request.user).first()
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response({'success': True, 'data': WorkspaceSerializer(workspace).data})

    if member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند تنظیمات را تغییر دهد', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    serializer = WorkspaceSerializer(workspace, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'success': False, 'error': str(serializer.errors), 'code': 'VALIDATION_ERROR'},
                        status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response({'success': True, 'data': serializer.data})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def member_list(request, workspace_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id, is_active=True)
    except Workspace.DoesNotExist:
        return Response({'success': False, 'error': 'فضای کاری یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    member = WorkspaceMember.objects.filter(workspace=workspace, user=request.user).first()
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        members = WorkspaceMember.objects.filter(workspace=workspace).select_related('user')
        return Response({'success': True, 'data': WorkspaceMemberSerializer(members, many=True).data})

    if member.role != 'admin':
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند عضو اضافه کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    serializer = AddMemberSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'error': str(serializer.errors), 'code': 'VALIDATION_ERROR'},
                        status=status.HTTP_400_BAD_REQUEST)

    from users.models import User
    try:
        user = User.objects.get(phone_number=serializer.validated_data['phone_number'])
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'کاربر با این شماره یافت نشد', 'code': 'USER_NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    if WorkspaceMember.objects.filter(workspace=workspace, user=user).exists():
        return Response({'success': False, 'error': 'این کاربر قبلاً عضو است', 'code': 'ALREADY_MEMBER'},
                        status=status.HTTP_400_BAD_REQUEST)

    new_member = WorkspaceMember.objects.create(
        workspace=workspace,
        user=user,
        role=serializer.validated_data['role'],
        added_by=request.user
    )
    return Response({'success': True, 'data': WorkspaceMemberSerializer(new_member).data},
                    status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def member_detail(request, workspace_id, member_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id, is_active=True)
    except Workspace.DoesNotExist:
        return Response({'success': False, 'error': 'فضای کاری یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    admin_member = WorkspaceMember.objects.filter(workspace=workspace, user=request.user, role='admin').first()
    if not admin_member:
        return Response({'success': False, 'error': 'فقط ادمین می‌تواند عضو حذف کند', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        member = WorkspaceMember.objects.get(id=member_id, workspace=workspace)
    except WorkspaceMember.DoesNotExist:
        return Response({'success': False, 'error': 'عضو یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    if member.user == workspace.owner:
        return Response({'success': False, 'error': 'نمی‌توان صاحب فضای کاری را حذف کرد', 'code': 'FORBIDDEN'},
                        status=status.HTTP_400_BAD_REQUEST)

    member.delete()
    return Response({'success': True, 'data': {'message': 'عضو با موفقیت حذف شد'}})
