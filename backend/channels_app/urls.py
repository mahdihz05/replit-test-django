from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:workspace_id>/channels/', views.channel_list),
    path('<uuid:workspace_id>/channels/verify/start/', views.verify_start),
    path('<uuid:workspace_id>/channels/verify/<str:token>/status/', views.verify_status),
    path('<uuid:workspace_id>/channels/verify/<str:token>/retry/', views.verify_retry),
    path('<uuid:workspace_id>/channels/<uuid:channel_id>/', views.channel_detail),
    path('<uuid:workspace_id>/channels/<uuid:channel_id>/test/', views.channel_test),
]
