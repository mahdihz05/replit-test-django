from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:workspace_id>/publish/jobs/', views.job_list),
    path('<uuid:workspace_id>/publish/jobs/<uuid:job_id>/', views.job_detail),
    path('<uuid:workspace_id>/publish/jobs/<uuid:job_id>/retry/', views.job_retry),
    path('<uuid:workspace_id>/publish/jobs/<uuid:job_id>/cancel/', views.cancel_job),
    path('<uuid:workspace_id>/publish/now/', views.publish_now),
    path('<uuid:workspace_id>/publish/schedule/', views.publish_schedule),
    path('<uuid:workspace_id>/publish/history/', views.publish_history),
    path('<uuid:workspace_id>/publish/queue/', views.publish_queue),
]
