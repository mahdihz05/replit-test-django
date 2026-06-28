from rest_framework import serializers
from .models import PublishJob, PublishLog
from channels_app.serializers import PublishChannelSerializer
from content.serializers import ContentSerializer


class PublishLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishLog
        fields = ['id', 'attempt_number', 'success', 'error_type', 'user_message', 'attempted_at']


class PublishJobSerializer(serializers.ModelSerializer):
    channel = PublishChannelSerializer(read_only=True)
    logs = PublishLogSerializer(many=True, read_only=True)
    content_title = serializers.CharField(source='content.title', read_only=True)

    class Meta:
        model = PublishJob
        fields = ['id', 'content', 'content_title', 'channel', 'status', 'scheduled_at',
                  'started_at', 'completed_at', 'attempt_count', 'max_attempts',
                  'next_retry_at', 'logs', 'created_at']
