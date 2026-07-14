from rest_framework import serializers
from .models import PublishChannel, ChannelVerification, LinkedInConnection, WordPressConnection


class PublishChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishChannel
        fields = ['id', 'platform', 'channel_type', 'name', 'external_id', 'username',
                  'is_verified', 'is_active', 'created_at']


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
