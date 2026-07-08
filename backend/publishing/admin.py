from django.contrib import admin
from .models import PublishAttachment, PublishJob, PublishLog


class PublishLogInline(admin.TabularInline):
    model = PublishLog
    extra = 0
    readonly_fields = ('attempt_number', 'success', 'error_type', 'error_message', 'user_message', 'api_response', 'attempted_at')
    ordering = ('-attempted_at',)
    can_delete = False


@admin.register(PublishAttachment)
class PublishAttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'workspace', 'content', 'media_type', 'mime_type', 'file_size_bytes', 'is_active', 'created_at')
    list_filter = ('media_type', 'is_active')
    search_fields = ('original_filename', 'workspace__name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('workspace', 'content')


@admin.register(PublishJob)
class PublishJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'content', 'channel', 'status', 'attempt_count', 'max_attempts', 'scheduled_at', 'completed_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('content__title', 'channel__name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'started_at', 'completed_at')
    raw_id_fields = ('content', 'channel')
    filter_horizontal = ('attachments',)
    inlines = [PublishLogInline]
    date_hierarchy = 'created_at'


@admin.register(PublishLog)
class PublishLogAdmin(admin.ModelAdmin):
    list_display = ('job', 'attempt_number', 'success', 'error_type', 'attempted_at')
    list_filter = ('success', 'error_type')
    search_fields = ('job__content__title', 'error_message')
    ordering = ('-attempted_at',)
    readonly_fields = ('attempted_at',)
    raw_id_fields = ('job',)
