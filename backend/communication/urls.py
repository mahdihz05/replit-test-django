from django.urls import path
from . import views


communication_urlpatterns = [
    path('<uuid:workspace_id>/communication/dashboard/', views.dashboard),
    path('<uuid:workspace_id>/communication/providers/', views.providers),
    path('<uuid:workspace_id>/communication/providers/<uuid:provider_id>/', views.provider_detail),
    path('<uuid:workspace_id>/communication/providers/<uuid:provider_id>/test/', views.provider_test),
    path('<uuid:workspace_id>/communication/contacts/', views.contacts),
    path('<uuid:workspace_id>/communication/contacts/<uuid:contact_id>/', views.contact_detail),
    path('<uuid:workspace_id>/communication/contact-groups/', views.groups),
    path('<uuid:workspace_id>/communication/contact-groups/<uuid:group_id>/', views.group_detail),
    path('<uuid:workspace_id>/communication/contact-groups/<uuid:group_id>/contacts/', views.group_add_contacts),
    path('<uuid:workspace_id>/communication/contact-groups/<uuid:group_id>/contacts/<uuid:contact_id>/', views.group_remove_contact),
    path('<uuid:workspace_id>/communication/templates/', views.templates),
    path('<uuid:workspace_id>/communication/templates/<uuid:template_id>/', views.template_detail),
    path('<uuid:workspace_id>/communication/templates/preview/', views.template_preview),
    path('<uuid:workspace_id>/communication/campaigns/', views.campaigns),
    path('<uuid:workspace_id>/communication/campaigns/<uuid:campaign_id>/', views.campaign_detail),
    path('<uuid:workspace_id>/communication/campaigns/<uuid:campaign_id>/preview/', views.campaign_preview_view),
    path('<uuid:workspace_id>/communication/campaigns/<uuid:campaign_id>/send-test/', views.campaign_send_test),
    path('<uuid:workspace_id>/communication/campaigns/<uuid:campaign_id>/start/', views.campaign_start),
    path('<uuid:workspace_id>/communication/campaigns/<uuid:campaign_id>/schedule/', views.campaign_schedule),
    path('<uuid:workspace_id>/communication/campaigns/<uuid:campaign_id>/cancel/', views.campaign_cancel),
    path('<uuid:workspace_id>/communication/campaigns/<uuid:campaign_id>/report/', views.campaign_report),
    path('<uuid:workspace_id>/communication/campaigns/<uuid:campaign_id>/messages/', views.campaign_messages),
    path('<uuid:workspace_id>/communication/contacts/import/preview/', views.import_preview),
    path('<uuid:workspace_id>/communication/contacts/import/<uuid:job_id>/confirm/', views.import_confirm),
    path('<uuid:workspace_id>/communication/contacts/import/<uuid:job_id>/preview/', views.import_remap_preview),
    path('<uuid:workspace_id>/communication/ai/<slug:action>/', views.ai_assist),
]
