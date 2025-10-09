from django.contrib import admin
from .models import SumUpCheckout, SumUpTransaction, SumUpRefund, ArtistPayout

@admin.register(SumUpCheckout)
class SumUpCheckoutAdmin(admin.ModelAdmin):
    list_display = ('checkout_reference', 'order', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('checkout_reference', 'checkout_id', 'order__email')
    readonly_fields = ('payment_id', 'created_at', 'updated_at', 'paid_at')
    ordering = ('-created_at',)

@admin.register(SumUpTransaction)
class SumUpTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_code', 'amount', 'status', 'platform_fee_amount', 'artist_earnings', 'timestamp')
    list_filter = ('status', 'payment_type', 'currency')
    search_fields = ('transaction_code', 'sumup_transaction_id')
    readonly_fields = ('transaction_id', 'created_at')
    ordering = ('-timestamp',)

@admin.register(SumUpRefund)
class SumUpRefundAdmin(admin.ModelAdmin):
    list_display = ('refund_id', 'transaction', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('refund_id', 'sumup_refund_id')
    readonly_fields = ('created_at', 'processed_at')

@admin.register(ArtistPayout)
class ArtistPayoutAdmin(admin.ModelAdmin):
    list_display = ('payout_id', 'artist', 'amount', 'status', 'period_start', 'period_end', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('payout_id', 'artist__username', 'reference_number')
    readonly_fields = ('created_at', 'processed_at')