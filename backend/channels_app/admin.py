from django.contrib import admin
from .models import PublishChannel, ChannelVerification, LinkedInConnection, WordPressConnection


@admin.register(PublishChannel)
class PublishChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'platform', 'channel_type', 'is_verified', 'is_active', 'created_at')
    list_filter = ('platform', 'channel_type', 'is_verified', 'is_active')
    search_fields = ('name', 'username', 'external_id', 'workspace__name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('workspace',)
    # extra_data may contain platform credentials (e.g. website API keys); keep it out of admin
    exclude = ('extra_data',)


@admin.register(ChannelVerification)
class ChannelVerificationAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'requested_by', 'platform', 'name', 'status', 'expires_at', 'created_at')
    list_filter = ('platform', 'status')
    search_fields = ('workspace__name', 'requested_by__phone_number', 'name')
    ordering = ('-created_at',)
    # token is a one-time verification secret — show only in detail (read-only) not in search/list
    readonly_fields = ('token', 'created_at')
    raw_id_fields = ('workspace', 'requested_by', 'channel')


@admin.register(LinkedInConnection)
class LinkedInConnectionAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'user', 'platform_target', 'status', 'is_active', 'connected_at')
    list_filter = ('platform_target', 'status', 'is_active')
    search_fields = ('workspace__name', 'user__phone_number')
    ordering = ('-connected_at',)
    readonly_fields = ('id', 'connected_at')
    raw_id_fields = ('workspace', 'user')
    # Exclude OAuth tokens — sensitive credentials, not meant to be viewed after storage
    exclude = ('access_token', 'refresh_token')


@admin.register(WordPressConnection)
class WordPressConnectionAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'user', 'site_url', 'wp_username', 'status', 'is_active', 'connected_at')
    list_filter = ('status', 'is_active')
    search_fields = ('workspace__name', 'user__phone_number', 'site_url', 'wp_username')
    ordering = ('-connected_at',)
    readonly_fields = ('id', 'connected_at')
    raw_id_fields = ('workspace', 'user')
    # Exclude application password — sensitive credential
    exclude = ('application_password',)
