from django.urls import path
from . import views

ai_urlpatterns = [
    path('<uuid:workspace_id>/ai/chat/sessions/', views.chat_sessions),
    path('<uuid:workspace_id>/ai/chat/sessions/<uuid:session_id>/', views.chat_session_detail),
    path('<uuid:workspace_id>/ai/chat/sessions/<uuid:session_id>/messages/', views.send_message),
    path('<uuid:workspace_id>/ai/generate/text/', views.generate_text),
    path('<uuid:workspace_id>/ai/generate/image/', views.generate_image_view),
    path('<uuid:workspace_id>/ai/generate/rewrite/', views.rewrite_text),
    path('<uuid:workspace_id>/ai/generate/titles/', views.suggest_titles),
    path('<uuid:workspace_id>/ai/generate/hashtags/', views.suggest_hashtags),
    path('<uuid:workspace_id>/ai/generate/cta/', views.generate_cta),
]

urlpatterns = ai_urlpatterns
