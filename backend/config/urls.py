from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from bots.telegram_bot import telegram_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/workspaces/', include('workspaces.urls')),
    path('api/webhooks/telegram/', telegram_webhook),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
