from django.db import models
from django.conf import settings
from orders.models import Order
from decimal import Decimal
import uuid
from django.utils import timezone


class SumUpCheckout(models.Model):
    """SumUp checkout session for payment processing."""
    CHECKOUT_STATUS_CHOICES = [
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    # Internal reference
    payment_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False
    )
    
    # SumUp checkout fields
    checkout_reference = models.CharField(
        max_length=255,
        unique=True,
        help_text="Our reference sent to SumUp"
    )
    sumup_checkout_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID returned by SumUp"
    )
    
    # Related records
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='checkouts'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_checkouts'
    )
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='artist_checkouts',
        limit_choices_to={'user_type': 'artist'}
    )
    
    # Checkout details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    description = models.CharField(max_length=255)
    merchant_code = models.CharField(
        max_length=50,
        help_text="SumUp merchant code"
    )
    
    # URLs for SumUp
    return_url = models.URLField(
        help_text="Where to send status after payment"
    )
    redirect_url = models.URLField(
        help_text="Where user goes after payment",
        blank=True
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=CHECKOUT_STATUS_CHOICES,
        default='created', 
        db_index=True
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Checkout expiration time from SumUp"
    )
    
    # Response data from SumUp
    sumup_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Full response from SumUp API"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Checkout {self.checkout_reference} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.payment_id:
            prefix = "CHK"
            unique_id = str(uuid.uuid4().hex)[:10].upper()
            self.payment_id = f"{prefix}-{unique_id}"
        
        if not self.checkout_reference:
            # Generate unique checkout reference for SumUp
            self.checkout_reference = str(uuid.uuid4())
            
        super().save(*args, **kwargs)


class SumUpTransaction(models.Model):
    """Completed SumUp transactions."""
    TRANSACTION_STATUS_CHOICES = [
        ('successful', 'Successful'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('ecom', 'E-commerce'),
        ('recurring', 'Recurring'),
        ('moto', 'Mail/Phone Order'),
    ]
    
    # Transaction identification
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False
    )
    checkout = models.ForeignKey(
        SumUpCheckout,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    # SumUp transaction fields
    sumup_transaction_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Transaction ID from SumUp"
    )
    transaction_code = models.CharField(
        max_length=255,
        unique=True,
        help_text="Transaction code from SumUp"
    )
    
    # Transaction details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    status = models.CharField(
        max_length=20,
        choices=TRANSACTION_STATUS_CHOICES
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='ecom'
    )
    
    # Card information (from SumUp)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_type = models.CharField(max_length=20, blank=True)
    entry_mode = models.CharField(max_length=50, blank=True)
    auth_code = models.CharField(max_length=50, blank=True)
    
    # Platform fees and earnings
    platform_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00')
    )
    platform_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    artist_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # VAT if applicable
    vat_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # SumUp internal reference
    internal_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="SumUp internal ID"
    )
    
    # Full response
    sumup_response = models.JSONField(null=True, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(help_text="Transaction time from SumUp", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Transaction {self.transaction_code} - £{self.amount}"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            prefix = "TXN"
            unique_id = str(uuid.uuid4().hex)[:10].upper()
            self.transaction_id = f"{prefix}-{unique_id}"
        
        # Calculate fees
        if self.amount is not None:
            self.platform_fee_amount = (self.amount * self.platform_fee_percentage) / 100
            self.artist_earnings = self.amount - self.platform_fee_amount

            
        super().save(*args, **kwargs)


class SumUpRefund(models.Model):
    """Refunds processed through SumUp."""
    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]
    
    refund_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False
    )
    transaction = models.ForeignKey(
        SumUpTransaction,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    
    # Refund details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS_CHOICES,
        default='pending'
    )
    
    # SumUp response
    sumup_refund_id = models.CharField(max_length=255, blank=True)
    sumup_response = models.JSONField(null=True, blank=True)
    
    # Processing info
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        artist_label = getattr(self.artist, "get_full_name", None)
        if callable(artist_label):
            name = self.artist.get_full_name()
        else:
            name = getattr(self.artist, "username", str(self.artist))
        return f"Payout {self.payout_id} to {name}"


    def save(self, *args, **kwargs):
        if not self.refund_id:
            prefix = "RFD"
            unique_id = str(uuid.uuid4().hex)[:8].upper()
            self.refund_id = f"{prefix}-{unique_id}"
        super().save(*args, **kwargs)


class SubscriptionPayment(models.Model):
    """Payments for artist subscriptions (also via SumUp)."""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]
    
    payment_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False
    )
    subscription = models.ForeignKey(
        'subscriptions.Subscription',
        on_delete=models.CASCADE,
        related_name='subscription_payments'
    )
    invoice = models.ForeignKey(
        'subscriptions.SubscriptionInvoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP', db_index=True)
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    
    # SumUp checkout reference
    checkout_reference = models.CharField(max_length=255, blank=True)
    sumup_transaction_code = models.CharField(max_length=255, blank=True)
    sumup_response = models.JSONField(null=True, blank=True)
    
    # Payment metadata
    description = models.CharField(max_length=255)
    failure_reason = models.TextField(blank=True)
    attempts = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Subscription Payment {self.payment_id} - £{self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_id:
            prefix = "SUBPAY"
            unique_id = str(uuid.uuid4().hex)[:8].upper()
            self.payment_id = f"{prefix}-{unique_id}"
        super().save(*args, **kwargs)


class ArtistPayout(models.Model):
    """Payouts to artists from their sales."""
    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    payout_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False
    )
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payouts',
        limit_choices_to={'user_type': 'artist'}
    )
    
    # Payout details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    status = models.CharField(
        max_length=20,
        choices=PAYOUT_STATUS_CHOICES,
        default='pending'
    )
    
    # Period covered
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Transactions included
    transactions = models.ManyToManyField(
        SumUpTransaction,
        related_name='artist_payouts'
    )
    
    # Bank details
    bank_account_name = models.CharField(max_length=100)
    bank_account_number = models.CharField(max_length=20)
    bank_sort_code = models.CharField(max_length=10)
    
    # Processing
    reference_number = models.CharField(max_length=100, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payouts'
    )
    
    # Summary
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        artist_label = getattr(self.artist, "get_full_name", None)
        if callable(artist_label):
            name = self.artist.get_full_name()
        else:
            name = getattr(self.artist, "username", str(self.artist))
        return f"Payout {self.payout_id} to {name}"

    def save(self, *args, **kwargs):
        if not self.payout_id:
            prefix = "PO"
            unique_id = str(uuid.uuid4().hex)[:10].upper()
            self.payout_id = f"{prefix}-{unique_id}"
        super().save(*args, **kwargs)

# payments/models.py


class Artist(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

class ArtistSumUpAuth(models.Model):
    """Stores OAuth tokens per artist so we can create checkouts on THEIR account."""
    artist = models.OneToOneField(Artist, on_delete=models.CASCADE, related_name="sumup")
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_type = models.CharField(max_length=20, default="Bearer")
    expires_at = models.DateTimeField()  # when the access token expires
    scope = models.CharField(max_length=255, blank=True, default="")

class Order(models.Model):
    """Your platform order for a given artist's product (artwork/ticket)."""
    artist = models.ForeignKey(Artist, on_delete=models.PROTECT, related_name="orders")
    reference = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=200)
    amount_gbp = models.DecimalField(max_digits=10, decimal_places=2)
    buyer_email = models.EmailField()
    status = models.CharField(max_length=16, default="PENDING")  # PENDING/PAID/FAILED
    created_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    gateway = models.CharField(max_length=20, default="sumup")
    checkout_id = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, default="PENDING")  # SUCCESSFUL/FAILED/PENDING
    raw = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

class Subscription(models.Model):
    """Your monthly platform fee agreement with the artist."""
    artist = models.OneToOneField(Artist, on_delete=models.CASCADE, related_name="subscription")
    amount_gbp = models.DecimalField(max_digits=10, decimal_places=2, default=25.00)
    is_active = models.BooleanField(default=True)
    # Either store a CityPay token OR a SumUp card token depending on the PSP you pick:
    citypay_token = models.CharField(max_length=200, blank=True, default="")
    sumup_token = models.CharField(max_length=200, blank=True, default="")  # if you go all-in on SumUp
    next_charge_date = models.DateField(null=True, blank=True)  # set after first payment
