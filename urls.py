# jersey_artwork/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("cart/", include(("cart.urls", "cart"), namespace="cart")),
    path("orders/", include(("orders.urls", "orders"), namespace="orders")),
    path("payments/", include(("payments.urls", "payments"), namespace="payments")),
    path("subscriptions/", include(("subscriptions.urls", "subscriptions"), namespace="subscriptions")),
    path("", include(("artworks.urls", "artworks"), namespace="artworks")),  # 👈 app at root
]
