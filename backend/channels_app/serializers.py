from rest_framework import serializers
from .models import PublishChannel, ChannelVerification


class PublishChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishChannel
        fields = ['id', 'platform', 'channel_type', 'name', 'external_id', 'username',
                  'is_verified', 'is_active', 'created_at']


class ChannelVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelVerification
        fields = ['id', 'platform', 'name', 'channel_type', 'token', 'status', 'expires_at', 'created_at']
