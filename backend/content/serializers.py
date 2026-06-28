from rest_framework import serializers
from .models import Content, ContentVersion


class ContentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentVersion
        fields = ['id', 'version_number', 'body', 'source', 'ai_model', 'created_at']


class ContentSerializer(serializers.ModelSerializer):
    created_by_phone = serializers.CharField(source='created_by.phone_number', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = [
            'id', 'title', 'body', 'status', 'language', 'goal', 'tags',
            'image', 'image_url', 'scheduled_at', 'published_at',
            'created_by', 'created_by_phone', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'published_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ContentInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ['title', 'body', 'status', 'language', 'goal', 'tags', 'scheduled_at']
