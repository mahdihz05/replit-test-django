from django.contrib import admin
from .models import GenerationBatch, GeneratedItem, AIChatSession, AIChatMessage


class GeneratedItemInline(admin.TabularInline):
    model = GeneratedItem
    extra = 0
    readonly_fields = ('id', 'item_type', 'order', 'created_at')
    fields = ('item_type', 'order', 'content', 'image', 'saved_as_draft', 'created_at')
    ordering = ('order',)
    can_delete = False


@admin.register(GenerationBatch)
class GenerationBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'workspace', 'user', 'mode', 'capability', 'status', 'image_status', 'wallet_cost_charged', 'created_at')
    list_filter = ('mode', 'status', 'image_status', 'capability', 'is_active')
    search_fields = ('workspace__name', 'user__phone_number', 'topic', 'capability')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('workspace', 'user')
    inlines = [GeneratedItemInline]
    date_hierarchy = 'created_at'


@admin.register(GeneratedItem)
class GeneratedItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'batch', 'item_type', 'order', 'saved_as_draft', 'created_at')
    list_filter = ('item_type', 'saved_as_draft')
    search_fields = ('batch__workspace__name',)
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('batch',)


class AIChatMessageInline(admin.TabularInline):
    model = AIChatMessage
    extra = 0
    readonly_fields = ('role', 'type', 'body', 'image_url', 'metadata', 'created_at')
    ordering = ('created_at',)
    can_delete = False


@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'workspace', 'user', 'created_at', 'updated_at')
    search_fields = ('title', 'workspace__name', 'user__phone_number')
    ordering = ('-updated_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('workspace', 'user', 'content')
    inlines = [AIChatMessageInline]


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'type', 'created_at')
    list_filter = ('role', 'type')
    search_fields = ('session__title', 'body')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    raw_id_fields = ('session',)
