from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.CartView.as_view(), name='view'),
    path('add/<int:artwork_id>/', views.AddToCartView.as_view(), name='add'),
    path('update/<int:item_id>/', views.UpdateCartItemView.as_view(), name='update'),
    path('remove/<int:item_id>/', views.RemoveFromCartView.as_view(), name='remove'),
    path('clear/', views.ClearCartView.as_view(), name='clear'),
    path('save/<int:artwork_id>/', views.SaveForLaterView.as_view(), name='save'),
    path('move-to-cart/<int:item_id>/', views.MoveToCartView.as_view(), name='move_to_cart'),
]