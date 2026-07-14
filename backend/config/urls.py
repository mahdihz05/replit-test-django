from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as serve_static

from bots.telegram_bot import telegram_webhook
from channels_app.views import linkedin_connect_callback

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/linkedin/callback/', linkedin_connect_callback),
    path('api/auth/', include('users.urls')),
    path('api/workspaces/', include('workspaces.urls')),
    path('api/webhooks/telegram/', telegram_webhook),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, 'SERVE_MEDIA_FILES', False):
    # Explicit local-development fallback when DEBUG is disabled by the host
    # environment. Production deployments should serve MEDIA_ROOT directly.
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_static, {'document_root': settings.MEDIA_ROOT}),
    ]
