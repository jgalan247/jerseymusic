from django.db import models
from django.conf import settings
from accounts.models import User
from events.models import Event
from decimal import Decimal
import uuid


class Order(models.Model):
    """Main order model."""
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('processing', 'Processing'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Order identification
    order_number = models.CharField(
        max_length=100,
        unique=True,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )
    
    # Contact information (saved at time of order)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Delivery information
    delivery_first_name = models.CharField(max_length=50)
    delivery_last_name = models.CharField(max_length=50)
    delivery_address_line_1 = models.CharField(max_length=255)
    delivery_address_line_2 = models.CharField(max_length=255, blank=True)
    delivery_parish = models.CharField(max_length=50, choices=[
        ('st_helier', 'St. Helier'),
        ('st_brelade', 'St. Brelade'),
        ('st_clement', 'St. Clement'),
        ('st_john', 'St. John'),
        ('st_lawrence', 'St. Lawrence'),
        ('st_martin', 'St. Martin'),
        ('st_ouen', 'St. Ouen'),
        ('st_peter', 'St. Peter'),
        ('st_saviour', 'St. Saviour'),
        ('trinity', 'Trinity'),
        ('st_mary', 'St. Mary'),
        ('grouville', 'Grouville'),
    ])
    delivery_postcode = models.CharField(max_length=10)
    
    # Billing information (if different from delivery)
    billing_same_as_delivery = models.BooleanField(default=True)
    billing_first_name = models.CharField(max_length=50, blank=True)
    billing_last_name = models.CharField(max_length=50, blank=True)
    billing_address_line_1 = models.CharField(max_length=255, blank=True)
    billing_address_line_2 = models.CharField(max_length=255, blank=True)
    billing_parish = models.CharField(max_length=50, blank=True)
    billing_postcode = models.CharField(max_length=10, blank=True)
    
    # Order details
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment information
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery tracking
    delivery_method = models.CharField(
        max_length=50,
        default='standard',
        choices=[
            ('collection', 'Collection'),
            ('standard', 'Standard Delivery'),
            ('express', 'Express Delivery'),
        ]
    )
    tracking_number = models.CharField(max_length=255, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    customer_note = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            prefix = "JE"  # Jersey Events
            unique_id = str(uuid.uuid4().hex)[:8].upper()
            self.order_number = f"{prefix}-{unique_id}"
        super().save(*args, **kwargs)

    @property
    def can_cancel(self):
        """Check if order can be cancelled."""
        # Test expects delivered=False, so remove it
        return self.status in ['pending', 'confirmed', 'processing']

    @property
    def full_name(self):
        """Get customer full name."""
        return f"{self.delivery_first_name} {self.delivery_last_name}"

    @property
    def full_address(self):
        """Get formatted delivery address."""
        lines = [
            self.delivery_address_line_1,
            self.delivery_address_line_2,
            self.delivery_parish,
            self.delivery_postcode,
            "Jersey"
        ]
        return ", ".join(filter(None, lines))

    def calculate_commission(self):
        """Calculate artist commissions for this order."""
        commissions = []
        for item in self.items.all():
            if hasattr(item.artwork.artist, 'artistprofile'):
                commission_rate = item.artwork.artist.artistprofile.commission_rate
                commission_amount = (item.price * item.quantity * commission_rate) / 100
                commissions.append({
                    'artist': item.artwork.artist,
                    'amount': commission_amount,
                    'rate': commission_rate
                })
        return commissions


class OrderItem(models.Model):
    """Individual items within an order."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.SET_NULL,
        null=True
    )
    
    # Store event details at time of order
    event_title = models.CharField(max_length=200)
    event_organiser = models.CharField(max_length=100)
    event_date = models.DateField(null=True)
    venue_name = models.CharField(max_length=200)
    
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Commission tracking
    artist_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.quantity}x {self.event_title}"

    def save(self, *args, **kwargs):
        # Calculate total
        self.total = Decimal(str(self.quantity)) * self.price
        
        # Store artwork details for historical record
        if self.event and not self.event_title:
            self.event_title = self.event.title
            self.event_organiser = self.event.organiser.get_full_name()
            self.event_date = self.event.event_date
            self.venue_name = self.event.venue_name
            
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Order status histories"

    def __str__(self):
        return f"Order {self.order.order_number}: {self.status}"


class Refund(models.Model):
    """Handle refunds for orders."""
    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    reason = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS_CHOICES,
        default='pending'
    )
    
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    
    admin_note = models.TextField(blank=True)
    refund_transaction_id = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund for Order {self.order.order_number}"

class RefundRequest(models.Model):
    """Track refund requests between customers and artists."""
    REFUND_STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('artist_reviewing', 'Artist Reviewing'),
        ('approved', 'Approved by Artist'),
        ('rejected', 'Rejected'),
        ('completed', 'Refund Completed'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refund_requests')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refund_requests')
    artist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='artist_refunds')
    
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='requested')
    
    # Artist response
    artist_response = models.TextField(blank=True)
    artist_approved = models.BooleanField(default=False)
    
    # Communication thread
    customer_message = models.TextField(blank=True)
    artist_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
