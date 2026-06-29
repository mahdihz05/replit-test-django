from django.urls import path
from . import views

urlpatterns = [
    path('workspaces/<uuid:workspace_id>/publish/jobs/', views.job_list),
    path('workspaces/<uuid:workspace_id>/publish/jobs/<uuid:job_id>/', views.job_detail),
    path('workspaces/<uuid:workspace_id>/publish/jobs/<uuid:job_id>/retry/', views.job_retry),
    path('workspaces/<uuid:workspace_id>/publish/jobs/<uuid:job_id>/cancel/', views.cancel_job),
    path('workspaces/<uuid:workspace_id>/publish/now/', views.publish_now),
    path('workspaces/<uuid:workspace_id>/publish/schedule/', views.publish_schedule),
    path('workspaces/<uuid:workspace_id>/publish/history/', views.publish_history),
    path('workspaces/<uuid:workspace_id>/publish/queue/', views.publish_queue),
]
