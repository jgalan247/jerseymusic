# events/urls.py  (PROJECT ROOT router)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('cart/', include(('cart.urls', 'cart'), namespace='cart')),
    path('orders/', include(('orders.urls', 'orders'), namespace='orders')),
    path('payments/', include(('payments.urls', 'payments'), namespace='payments')),
    # path('subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),  # DISABLED - Using pay-per-event model
    path('analytics/', include(('analytics.urls', 'analytics'), namespace='analytics')),
    # path('pricing/', views.pricing, name='pricing'),
    path("", include(("events.app_urls", "events"), namespace="events")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
