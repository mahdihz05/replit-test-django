from django.contrib import admin
from .models import Content, ContentVersion


class ContentVersionInline(admin.TabularInline):
    model = ContentVersion
    extra = 0
    readonly_fields = ('version_number', 'source', 'ai_model', 'created_at')
    fields = ('version_number', 'source', 'ai_model', 'body', 'created_at')
    ordering = ('-version_number',)
    can_delete = False


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'workspace', 'created_by', 'status', 'language', 'is_active', 'created_at')
    list_filter = ('status', 'language', 'is_active')
    search_fields = ('title', 'body', 'workspace__name', 'created_by__phone_number')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('workspace', 'created_by')
    inlines = [ContentVersionInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {'fields': ('id', 'workspace', 'created_by', 'title', 'body')}),
        ('وضعیت', {'fields': ('status', 'is_active', 'language')}),
        ('محتوا', {'fields': ('goal', 'tags', 'image')}),
        ('زمان‌بندی', {'fields': ('scheduled_at', 'published_at')}),
        ('تاریخ', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(ContentVersion)
class ContentVersionAdmin(admin.ModelAdmin):
    list_display = ('content', 'version_number', 'source', 'ai_model', 'created_at')
    list_filter = ('source',)
    search_fields = ('content__title',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    raw_id_fields = ('content',)
