from django.urls import path
from . import views

content_urlpatterns = [
    path('<uuid:workspace_id>/contents/', views.content_list),
    path('<uuid:workspace_id>/contents/<uuid:content_id>/', views.content_detail),
    path('<uuid:workspace_id>/contents/<uuid:content_id>/versions/', views.content_versions),
    path('<uuid:workspace_id>/contents/<uuid:content_id>/publish/', views.publish_content),
]

urlpatterns = content_urlpatterns
