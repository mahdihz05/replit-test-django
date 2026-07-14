from django.contrib import admin

from .models import Campaign, CampaignMessage, CommunicationProvider, Contact, ContactGroup, ImportJob, MessageTemplate


@admin.register(CommunicationProvider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'type', 'provider_key', 'status', 'last_test_status', 'updated_at')
    exclude = ('encrypted_credentials',)
    list_filter = ('type', 'provider_key', 'status', 'last_test_status')


admin.site.register(Contact)
admin.site.register(ContactGroup)
admin.site.register(MessageTemplate)
admin.site.register(Campaign)
admin.site.register(CampaignMessage)
admin.site.register(ImportJob)
