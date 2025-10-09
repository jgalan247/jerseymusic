"""
Listing fee models for the event platform.
"""

from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid

class ListingFee(models.Model):
    """Model to track listing fees for events."""

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    # Event and organizer
    event = models.OneToOneField(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='listing_fee'
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='listing_fees'
    )

    # Fee details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('15.00'),
        help_text="Listing fee amount in GBP"
    )
    currency = models.CharField(max_length=3, default='GBP')

    # Payment tracking
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        blank=True
    )
    sumup_checkout_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="SumUp checkout ID for tracking"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Additional data
    payment_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Store SumUp payment response data"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Listing fee for {self.event.title} - {self.payment_status}"

    def save(self, *args, **kwargs):
        if not self.payment_reference:
            # Generate unique payment reference
            prefix = "LF"  # Listing Fee
            unique_id = str(uuid.uuid4().hex)[:8].upper()
            self.payment_reference = f"{prefix}-{unique_id}"
        super().save(*args, **kwargs)

    @property
    def is_paid(self):
        """Check if listing fee has been paid."""
        return self.payment_status == 'paid'

    @property
    def can_publish_event(self):
        """Check if event can be published (fee paid)."""
        return self.is_paid


class ListingFeeConfig(models.Model):
    """Configuration for listing fees."""

    # Fee structure
    standard_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('15.00'),
        help_text="Standard listing fee for events"
    )
    premium_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('25.00'),
        help_text="Premium listing fee (e.g., featured events)"
    )
    currency = models.CharField(max_length=3, default='GBP')

    # Settings
    require_payment_before_publish = models.BooleanField(
        default=True,
        help_text="Require listing fee payment before event can be published"
    )
    grace_period_hours = models.IntegerField(
        default=24,
        help_text="Hours to complete payment after event creation"
    )

    # Platform details
    platform_name = models.CharField(
        max_length=100,
        default="Jersey Events",
        help_text="Platform name for payment descriptions"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Listing Fee Configuration"
        verbose_name_plural = "Listing Fee Configurations"

    def __str__(self):
        return f"Listing Fee Config - £{self.standard_fee}"

    @classmethod
    def get_config(cls):
        """Get the current listing fee configuration."""
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'standard_fee': Decimal('15.00'),
                'premium_fee': Decimal('25.00'),
            }
        )
        return config