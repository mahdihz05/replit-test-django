from rest_framework import serializers
from .models import Workspace, WorkspaceMember


class MembershipSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ['id', 'workspace', 'workspace_name', 'role', 'created_at']


class WorkspaceSerializer(serializers.ModelSerializer):
    owner_phone = serializers.CharField(source='owner.phone_number', read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'owner', 'owner_phone', 'is_active', 'member_count', 'created_at', 'updated_at']
        read_only_fields = ['owner']

    def get_member_count(self, obj):
        return obj.members.count()


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ['id', 'user_id', 'user_phone', 'user_name', 'role', 'created_at']


class AddMemberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)
    role = serializers.ChoiceField(choices=['admin', 'manager'], default='manager')
