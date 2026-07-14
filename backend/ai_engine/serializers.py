from rest_framework import serializers
from .models import AIChatSession, AIChatMessage, GenerationBatch, GeneratedItem


class GeneratedItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedItem
        fields = ['id', 'item_type', 'order', 'content', 'image', 'image_url', 'saved_as_draft', 'created_at']

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class GenerationBatchSerializer(serializers.ModelSerializer):
    items = GeneratedItemSerializer(many=True, read_only=True)
    image_item = serializers.SerializerMethodField()

    class Meta:
        model = GenerationBatch
        fields = ['id', 'mode', 'capability', 'topic', 'tone', 'platform',
                  'variant_count', 'status', 'image_status', 'wallet_cost_charged',
                  'created_at', 'items', 'image_item']

    def get_image_item(self, obj):
        image = obj.items.filter(item_type='image').first()
        if image:
            return GeneratedItemSerializer(image, context=self.context).data
        return None


class AIChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIChatMessage
        fields = ['id', 'role', 'type', 'body', 'image_url', 'metadata', 'created_at']


class AIChatSessionSerializer(serializers.ModelSerializer):
    messages = AIChatMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = AIChatSession
        fields = ['id', 'title', 'content', 'created_at', 'updated_at', 'messages', 'last_message']

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {'body': last.body[:100], 'created_at': last.created_at}
        return None


class AIChatSessionListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = AIChatSession
        fields = ['id', 'title', 'content', 'created_at', 'updated_at', 'last_message']

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {'body': last.body[:100], 'created_at': last.created_at}
        return None
