# artworks/urls.py  (PROJECT ROOT router)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('cart/', include(('cart.urls', 'cart'), namespace='cart')),
    path('orders/', include(('orders.urls', 'orders'), namespace='orders')),
    path('payments/', include(('payments.urls', 'payments'), namespace='payments')),
    path('subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),

    path("", include(("artworks.app_urls", "artworks"), namespace="artworks")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
