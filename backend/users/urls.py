from django.urls import path
from . import views

urlpatterns = [
    path('otp/request/', views.otp_request),
    path('otp/verify/', views.otp_verify),
    path('token/refresh/', views.token_refresh),
    path('me/', views.me),
]
