from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:workspace_id>/channels/', views.channel_list),
    path('<uuid:workspace_id>/channels/verify/start/', views.verify_start),
    path('<uuid:workspace_id>/channels/verify/<str:token>/status/', views.verify_status),
    path('<uuid:workspace_id>/channels/verify/<str:token>/retry/', views.verify_retry),
    path('<uuid:workspace_id>/channels/verify/<str:token>/confirm/', views.verify_manual),
    path('<uuid:workspace_id>/channels/<str:channel_id>/', views.channel_detail),
    path('<uuid:workspace_id>/channels/<str:channel_id>/test/', views.channel_test),
    path('<uuid:workspace_id>/telegram-bot-status/', views.telegram_bot_status),

    # LinkedIn OAuth
    path('<uuid:workspace_id>/linkedin/config/', views.linkedin_config_status),
    path('<uuid:workspace_id>/linkedin/connect/start/', views.linkedin_connect_start),
    path('linkedin/callback/', views.linkedin_connect_callback),
    path('<uuid:workspace_id>/linkedin/<uuid:connection_id>/disconnect/', views.linkedin_disconnect),

    # WordPress Application Passwords
    path('<uuid:workspace_id>/wordpress/connect/start/', views.wordpress_connect_start),
    path('<uuid:workspace_id>/wordpress/callback/', views.wordpress_connect_callback),
    path('<uuid:workspace_id>/wordpress/<uuid:connection_id>/disconnect/', views.wordpress_disconnect),
]
