from django.contrib import admin
from .models import Cart, CartItem, SavedItem

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'total_items', 'subtotal', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'user__email', 'session_key')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'event', 'quantity', 'price_at_time', 'total_price', 'added_at')
    list_filter = ('event__category', 'added_at')
    search_fields = ('cart__user__username', 'event__title')
    readonly_fields = ('added_at', 'updated_at')

@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'added_at')
    list_filter = ('event__category', 'added_at')
    search_fields = ('user__username', 'event__title')