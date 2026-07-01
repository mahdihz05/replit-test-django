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
    path('<uuid:workspace_id>/ai/generate/summary/', views.generate_summary),
    path('<uuid:workspace_id>/ai/generate/scenario/', views.generate_scenario),
    path('<uuid:workspace_id>/ai/generate/idea/', views.generate_idea),
    path('<uuid:workspace_id>/ai/generate/bundle/', views.generate_bundle),
    path('<uuid:workspace_id>/ai/generate/multi-variant/', views.generate_multi_variant),
    path('<uuid:workspace_id>/ai/generate/items/<uuid:item_id>/save/', views.save_generated_item),
]

urlpatterns = ai_urlpatterns
