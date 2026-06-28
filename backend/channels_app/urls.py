from django.urls import path
from . import views

urlpatterns = [
    path('workspaces/<uuid:workspace_id>/channels/', views.channel_list),
    path('workspaces/<uuid:workspace_id>/channels/verify/start/', views.verify_start),
    path('workspaces/<uuid:workspace_id>/channels/verify/<str:token>/status/', views.verify_status),
    path('workspaces/<uuid:workspace_id>/channels/<uuid:channel_id>/', views.channel_detail),
]
