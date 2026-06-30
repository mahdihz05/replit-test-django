from django.urls import path
from . import views
from content.urls import content_urlpatterns
from ai_engine.urls import ai_urlpatterns
from wallet.urls import wallet_urlpatterns
from channels_app.urls import urlpatterns as channel_urlpatterns
from publishing.urls import urlpatterns as publish_urlpatterns
from reports.urls import urlpatterns as report_urlpatterns

urlpatterns = [
    path('', views.workspace_list),
    path('<uuid:workspace_id>/', views.workspace_detail),
    path('<uuid:workspace_id>/members/', views.member_list),
    path('<uuid:workspace_id>/members/<int:member_id>/', views.member_detail),
] + content_urlpatterns + ai_urlpatterns + wallet_urlpatterns + channel_urlpatterns + publish_urlpatterns + report_urlpatterns
