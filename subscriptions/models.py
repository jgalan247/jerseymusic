from django.db import models
from django.conf import settings
from accounts.models import User
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
import uuid


class SubscriptionPlan(models.Model):
    """Subscription plans for artists to list on the platform."""
    PLAN_TYPE_CHOICES = [
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]
    
    BILLING_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]
    
    # Plan details
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE_CHOICES,
        default='basic'
    )
    description = models.TextField()
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    billing_period = models.CharField(
        max_length=20,
        choices=BILLING_PERIOD_CHOICES,
        default='monthly'
    )
    
    # Features and limits
    max_artworks = models.IntegerField(
        default=10,
        help_text="Maximum number of artworks artist can list"
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Platform commission percentage on sales"
    )
    featured_artworks = models.IntegerField(
        default=0,
        help_text="Number of featured artwork slots"
    )
    
    # Plan features (stored as JSON for flexibility)
    features = models.JSONField(
        default=dict,
        help_text="Plan features as key-value pairs"
    )
    
    # Visibility
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    
    # Trial period
    trial_days = models.IntegerField(
        default=0,
        help_text="Free trial period in days"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'price']

    def __str__(self):
        return f"{self.name} - £{self.price}/{self.get_billing_period_display()}"

    def get_period_days(self):
        """Get number of days in billing period."""
        if self.billing_period == 'monthly':
            return 30
        elif self.billing_period == 'quarterly':
            return 90
        elif self.billing_period == 'annual':
            return 365
        return 30


class Subscription(models.Model):
    """Artist subscription model."""
    
    STATUS_CHOICES = [
        ('trialing', 'Trial Period'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription',
        null=True,  # ADD THIS
        blank=True  # ADD THIS
    )
    def default_period_end():
        return timezone.now() + timedelta(days=30)
    
    # Pricing (captured at subscription time for history)
    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('15.00')
    )
    currency = models.CharField(max_length=3, default='GBP')
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='trialing'
    )
    
    # Dates
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(auto_now_add=True)
    current_period_end = models.DateTimeField(default=default_period_end)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Payment
    payment_method = models.CharField(max_length=50, blank=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    last_payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    next_billing_date = models.DateTimeField(default=default_period_end)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    


    class Meta:
        db_table = 'subscriptions'
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New subscription
            # Set trial period
            self.trial_end = timezone.now() + timedelta(days=settings.SUBSCRIPTION_CONFIG['TRIAL_DAYS'])
            self.current_period_end = self.trial_end
            self.next_billing_date = self.trial_end
            # Set price from current config
            self.monthly_price = settings.SUBSCRIPTION_CONFIG['MONTHLY_PRICE']
            self.currency = settings.SUBSCRIPTION_CONFIG['CURRENCY']
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Check if subscription allows artist to sell."""
        return self.status in ['trialing', 'active', 'past_due']
    
    @property
    def can_upload_artwork(self):
        """Check if artist can upload new artwork."""
        if not self.is_active:
            return False
        
        # Check artwork limit
        artwork_count = self.user.artworks.filter(status='active').count()
        max_artworks = settings.SUBSCRIPTION_CONFIG['FEATURES']['MAX_ARTWORKS']
        return artwork_count < max_artworks
    
    @property
    def days_until_renewal(self):
        """Days until next billing."""
        if self.next_billing_date:
            delta = self.next_billing_date - timezone.now()
            return max(0, delta.days)
        return 0
    
    def cancel(self, immediate=False):
        """Cancel subscription."""
        self.cancelled_at = timezone.now()
        if immediate:
            self.status = 'cancelled'
            self.current_period_end = timezone.now()
        else:
            # Cancel at end of period
            self.status = 'active'  # Keep active until period ends
        self.save()
    
    def charge_recurring_payment(self):
        """Process monthly payment."""
        from payments.services import PaymentService
        
        service = PaymentService()
        result = service.charge_subscription(
            subscription=self,
            amount=self.monthly_price
        )
        
        if result['success']:
            self.last_payment_date = timezone.now()
            self.last_payment_amount = self.monthly_price
            self.current_period_start = timezone.now()
            self.current_period_end = timezone.now() + timedelta(days=30)
            self.next_billing_date = self.current_period_end
            self.status = 'active'
            self.save()
            
            # Record payment
            SubscriptionPayment.objects.create(
                subscription=self,
                amount=self.monthly_price,
                status='succeeded',
                transaction_id=result.get('transaction_id')
            )
            return True
        else:
            self.status = 'past_due'
            self.save()
            return False


class SubscriptionPayment(models.Model):
    """Record of subscription payments."""
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    status = models.CharField(max_length=20)  # succeeded, failed, refunded
    transaction_id = models.CharField(max_length=255, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']



class SubscriptionInvoice(models.Model):
    """Invoices for subscription payments."""
    INVOICE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Invoice identification
    invoice_number = models.CharField(
        max_length=100,
        unique=True,
        editable=False
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    
    # Invoice details
    status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS_CHOICES,
        default='draft'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    
    # Billing period
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    
    # Payment information
    payment_due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)
    
    # SumUp integration (for subscription payments)
    sumup_payment_id = models.CharField(max_length=255, blank=True)
    sumup_response = models.JSONField(null=True, blank=True)
    
    # Invoice lines
    description = models.TextField()
    line_items = models.JSONField(
        default=dict,
        help_text="Detailed breakdown of charges"
    )
    
    # Refund tracking
    is_refunded = models.BooleanField(default=False)
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number} - £{self.amount}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number
            from datetime import datetime
            year = datetime.now().year
            month = datetime.now().month
            prefix = f"INV-{year}{month:02d}"
            unique_id = str(uuid.uuid4().hex)[:6].upper()
            self.invoice_number = f"{prefix}-{unique_id}"
        super().save(*args, **kwargs)


class SubscriptionUsage(models.Model):
    """Track subscription usage and limits."""
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    
    # Usage metrics
    month = models.DateField()
    artworks_added = models.IntegerField(default=0)
    artworks_sold = models.IntegerField(default=0)
    total_views = models.IntegerField(default=0)
    total_sales_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    commission_earned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Feature usage
    featured_artwork_days = models.IntegerField(default=0)
    api_calls = models.IntegerField(default=0)
    storage_used_mb = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month']
        unique_together = ['subscription', 'month']

    def __str__(self):
        return f"Usage for {self.subscription.artist.get_full_name()} - {self.month}"


class SubscriptionChange(models.Model):
    """Track subscription plan changes."""
    CHANGE_TYPE_CHOICES = [
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('renewal', 'Renewal'),
        ('cancellation', 'Cancellation'),
        ('reactivation', 'Reactivation'),
        ('pause', 'Pause'),
        ('resume', 'Resume'),
    ]
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='changes'
    )
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES
    )
    
    # Plan change details
    from_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        related_name='changes_from'
    )
    to_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        related_name='changes_to'
    )
    
    # Pricing changes
    from_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    to_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Change details
    reason = models.TextField(blank=True)
    effective_date = models.DateTimeField()
    
    # Who made the change
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='subscription_changes_made'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.change_type} - {self.subscription.artist.get_full_name()}"
