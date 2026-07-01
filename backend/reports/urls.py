from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:workspace_id>/dashboard/', views.dashboard_stats),
    path('<uuid:workspace_id>/reports/content/', views.content_report),
    path('<uuid:workspace_id>/reports/publishing/', views.publishing_report),
    path('<uuid:workspace_id>/reports/ai-usage/', views.ai_usage_report),
    path('<uuid:workspace_id>/reports/errors/', views.errors_report),
]
