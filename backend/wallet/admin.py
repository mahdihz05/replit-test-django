from django.contrib import admin
from .models import Wallet, WalletTransaction


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ('type', 'amount', 'description', 'created_at')
    ordering = ('-created_at',)
    can_delete = False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'balance', 'updated_at')
    search_fields = ('workspace__name',)
    readonly_fields = ('updated_at',)
    inlines = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'type', 'amount', 'description', 'created_at')
    list_filter = ('type',)
    search_fields = ('wallet__workspace__name', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
