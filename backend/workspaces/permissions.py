from rest_framework.permissions import BasePermission
from .models import WorkspaceMember


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


class IsWorkspaceMember(BasePermission):
    def has_permission(self, request, view):
        workspace_id = view.kwargs.get('workspace_id') or view.kwargs.get('wid')
        if not workspace_id:
            return False
        member = get_member(request.user, workspace_id)
        if not member:
            return False
        request.workspace_member = member
        return True


class IsWorkspaceAdmin(BasePermission):
    def has_permission(self, request, view):
        workspace_id = view.kwargs.get('workspace_id') or view.kwargs.get('wid')
        if not workspace_id:
            return False
        member = get_member(request.user, workspace_id)
        if not member or member.role != 'admin':
            return False
        request.workspace_member = member
        return True
