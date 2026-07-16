from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Workspace, WorkspaceMember
from .serializers import (
    AddMemberSerializer,
    UpdateMemberSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
)


def error_response(message, code, http_status):
    return Response(
        {'success': False, 'error': message, 'code': code},
        status=http_status,
    )


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
        return error_response(str(serializer.errors), 'VALIDATION_ERROR', status.HTTP_400_BAD_REQUEST)

    workspace = serializer.save(owner=request.user)
    WorkspaceMember.objects.create(
        workspace=workspace,
        user=request.user,
        role='admin',
        added_by=request.user,
    )
    from wallet.models import Wallet
    Wallet.objects.create(workspace=workspace)
    return Response(
        {'success': True, 'data': WorkspaceSerializer(workspace).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def workspace_detail(request, workspace_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id, is_active=True)
    except Workspace.DoesNotExist:
        return error_response('فضای کاری یافت نشد', 'NOT_FOUND', status.HTTP_404_NOT_FOUND)

    member = WorkspaceMember.objects.filter(workspace=workspace, user=request.user).first()
    if not member:
        return error_response('دسترسی ندارید', 'FORBIDDEN', status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response({'success': True, 'data': WorkspaceSerializer(workspace).data})

    if member.role != 'admin':
        return error_response(
            'فقط مدیر کل می‌تواند تنظیمات را تغییر دهد',
            'FORBIDDEN',
            status.HTTP_403_FORBIDDEN,
        )

    serializer = WorkspaceSerializer(workspace, data=request.data, partial=True)
    if not serializer.is_valid():
        return error_response(str(serializer.errors), 'VALIDATION_ERROR', status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response({'success': True, 'data': serializer.data})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def member_list(request, workspace_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id, is_active=True)
    except Workspace.DoesNotExist:
        return error_response('فضای کاری یافت نشد', 'NOT_FOUND', status.HTTP_404_NOT_FOUND)

    requesting_member = WorkspaceMember.objects.filter(
        workspace=workspace,
        user=request.user,
    ).first()
    if not requesting_member:
        return error_response('دسترسی ندارید', 'FORBIDDEN', status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        members = WorkspaceMember.objects.filter(workspace=workspace).select_related('user').order_by('created_at')
        return Response({'success': True, 'data': WorkspaceMemberSerializer(members, many=True).data})

    if requesting_member.role != 'admin':
        return error_response(
            'فقط مدیر کل می‌تواند عضو اضافه کند',
            'FORBIDDEN',
            status.HTTP_403_FORBIDDEN,
        )

    serializer = AddMemberSerializer(data=request.data)
    if not serializer.is_valid():
        message = next(iter(serializer.errors.values()))[0]
        return error_response(str(message), 'VALIDATION_ERROR', status.HTTP_400_BAD_REQUEST)

    from users.models import User
    try:
        user = User.objects.get(
            phone_number=serializer.validated_data['phone_number'],
            is_active=True,
        )
    except User.DoesNotExist:
        return error_response(
            'کاربر فعالی با این شماره یافت نشد',
            'USER_NOT_FOUND',
            status.HTTP_404_NOT_FOUND,
        )

    if WorkspaceMember.objects.filter(workspace=workspace, user=user).exists():
        return error_response(
            'این کاربر قبلاً عضو است',
            'ALREADY_MEMBER',
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            new_member = WorkspaceMember.objects.create(
                workspace=workspace,
                user=user,
                role=serializer.validated_data['role'],
                added_by=request.user,
            )
    except IntegrityError:
        return error_response(
            'این کاربر قبلاً عضو است',
            'ALREADY_MEMBER',
            status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {'success': True, 'data': WorkspaceMemberSerializer(new_member).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def member_detail(request, workspace_id, member_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id, is_active=True)
    except Workspace.DoesNotExist:
        return error_response('فضای کاری یافت نشد', 'NOT_FOUND', status.HTTP_404_NOT_FOUND)

    admin_member = WorkspaceMember.objects.filter(
        workspace=workspace,
        user=request.user,
        role='admin',
    ).first()
    if not admin_member:
        return error_response(
            'فقط مدیر کل می‌تواند اعضا را مدیریت کند',
            'FORBIDDEN',
            status.HTTP_403_FORBIDDEN,
        )

    try:
        member = WorkspaceMember.objects.select_related('user').get(
            id=member_id,
            workspace=workspace,
        )
    except WorkspaceMember.DoesNotExist:
        return error_response('عضو یافت نشد', 'NOT_FOUND', status.HTTP_404_NOT_FOUND)

    if member.user == workspace.owner:
        return error_response(
            'نقش یا عضویت مالک فضای کاری قابل تغییر نیست',
            'OWNER_MEMBERSHIP_PROTECTED',
            status.HTTP_400_BAD_REQUEST,
        )

    if request.method == 'PATCH':
        serializer = UpdateMemberSerializer(data=request.data)
        if not serializer.is_valid():
            message = next(iter(serializer.errors.values()))[0]
            return error_response(str(message), 'VALIDATION_ERROR', status.HTTP_400_BAD_REQUEST)
        member.role = serializer.validated_data['role']
        member.save(update_fields=['role'])
        return Response({'success': True, 'data': WorkspaceMemberSerializer(member).data})

    member.delete()
    return Response({'success': True, 'data': {'message': 'عضو با موفقیت حذف شد'}})
