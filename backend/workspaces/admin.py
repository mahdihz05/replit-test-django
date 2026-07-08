from django.contrib import admin
from .models import Workspace, WorkspaceMember


class WorkspaceMemberInline(admin.TabularInline):
    model = WorkspaceMember
    extra = 0
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'added_by')


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'owner__phone_number', 'owner__full_name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('owner',)
    inlines = [WorkspaceMemberInline]


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'workspace', 'role', 'added_by', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__phone_number', 'workspace__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'workspace', 'added_by')
