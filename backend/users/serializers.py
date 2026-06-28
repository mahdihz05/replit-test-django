from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'phone_number', 'full_name', 'created_at', 'memberships']

    def get_memberships(self, obj):
        from workspaces.serializers import MembershipSerializer
        memberships = obj.memberships.select_related('workspace').all()
        return MembershipSerializer(memberships, many=True).data


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name']


class OTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)

    def validate_phone_number(self, value):
        if not value.startswith('09') or len(value) != 11:
            raise serializers.ValidationError('شماره موبایل باید با 09 شروع شده و 11 رقم باشد')
        return value


class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)
    code = serializers.CharField(max_length=6)
