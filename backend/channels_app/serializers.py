from rest_framework import serializers
from .models import PublishChannel, ChannelVerification, LinkedInConnection, WordPressConnection


class PublishChannelSerializer(serializers.ModelSerializer):
    wordpress = serializers.SerializerMethodField()

    class Meta:
        model = PublishChannel
        fields = ['id', 'platform', 'channel_type', 'name', 'external_id', 'username',
                  'is_verified', 'is_active', 'created_at', 'wordpress']

    def get_wordpress(self, obj):
        if obj.platform != 'wordpress':
            return None
        connection_id = (obj.extra_data or {}).get('connection_id')
        connection = WordPressConnection.objects.filter(
            id=connection_id,
            workspace=obj.workspace,
        ).first()
        if not connection:
            return {'status': 'invalid', 'capabilities': {}, 'synced_at': None}
        return {
            'connection_id': str(connection.id),
            'status': connection.status,
            'site_name': connection.site_name or obj.name,
            'capabilities': connection.capabilities or {},
            'synced_at': connection.capabilities_synced_at,
        }


class ChannelVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelVerification
        fields = ['id', 'platform', 'name', 'channel_type', 'token', 'status', 'expires_at', 'created_at']


class LinkedInConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedInConnection
        fields = ['id', 'platform_target', 'person_urn', 'organization_urn', 'name',
                  'email', 'avatar_url', 'scopes', 'status', 'access_token_expires_at',
                  'refresh_token_expires_at', 'connected_at', 'disconnected_at', 'is_active']


class WordPressConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WordPressConnection
        fields = ['id', 'site_url', 'wp_username', 'status', 'connected_at', 'is_active']
