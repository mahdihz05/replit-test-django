from rest_framework import serializers
from .models import PublishJob, PublishLog, PublishAttachment
from channels_app.serializers import PublishChannelSerializer
from content.serializers import ContentSerializer


class PublishAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PublishAttachment
        fields = ['id', 'file_path', 'media_type', 'mime_type', 'file_size_bytes',
                  'original_filename', 'created_at', 'file_url']

    def get_file_url(self, obj):
        if obj.file_path.startswith('/'):
            return obj.file_path
        return f'/media/{obj.file_path}'


class PublishLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishLog
        fields = ['id', 'attempt_number', 'success', 'error_type', 'error_message', 'user_message', 'attempted_at']


class PublishJobSerializer(serializers.ModelSerializer):
    channel = PublishChannelSerializer(read_only=True)
    logs = PublishLogSerializer(many=True, read_only=True)
    content_title = serializers.CharField(source='content.title', read_only=True)
    attachments = PublishAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = PublishJob
        fields = ['id', 'content', 'content_title', 'channel', 'status', 'scheduled_at',
                  'started_at', 'completed_at', 'attempt_count', 'max_attempts',
                  'next_retry_at', 'platform_options', 'logs', 'attachments', 'created_at']
