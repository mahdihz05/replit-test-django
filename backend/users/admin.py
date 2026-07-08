from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'full_name', 'is_active', 'is_staff', 'is_superuser', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('phone_number', 'full_name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')

    fieldsets = (
        (None, {'fields': ('id', 'phone_number', 'password')}),
        ('اطلاعات شخصی', {'fields': ('full_name',)}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('تاریخ', {'fields': ('created_at', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )

    # Custom USERNAME_FIELD is phone_number
    add_form_template = None


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('phone_number',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    # code field intentionally excluded from list and form — OTPs are one-time secrets
    exclude = ('code',)
