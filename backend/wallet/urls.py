from django.urls import path
from . import views

wallet_urlpatterns = [
    path('<uuid:workspace_id>/wallet/', views.wallet_detail),
    path('<uuid:workspace_id>/wallet/transactions/', views.transaction_list),
    path('<uuid:workspace_id>/wallet/charge/', views.charge_wallet),
]

urlpatterns = wallet_urlpatterns
