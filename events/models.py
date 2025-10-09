from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from accounts.models import User
from decimal import Decimal
import uuid
import logging
import qrcode
from io import BytesIO
from django.core.files import File
from django.utils import timezone

logger = logging.getLogger(__name__)


class Category(models.Model):
    """Categories for organizing events."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        """Generate a unique slug for the category"""
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        # Check if slug exists and increment if needed
        while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug


class Event(models.Model):
    """Main event model for ticketing system."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('sold_out', 'Sold Out'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    organiser = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='events',
        limit_choices_to={'user_type': 'artist'}
    )

    # Event Details
    description = models.TextField()
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='events'
    )

    # Venue Information
    venue_name = models.CharField(max_length=200)
    venue_address = models.TextField()

    # Date and Time
    event_date = models.DateField()
    event_time = models.TimeField()

    # Ticketing
    capacity = models.PositiveIntegerField(
        help_text="Maximum number of tickets available. Maximum: 500 tickets for automatic pricing."
    )
    tickets_sold = models.PositiveIntegerField(default=0)
    ticket_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base ticket price in GBP"
    )

    # Payment Processing Fee Option
    processing_fee_passed_to_customer = models.BooleanField(
        default=False,
        help_text="If True, the 1.69% SumUp processing fee is added to the ticket price for customers. "
                  "If False, the organizer absorbs the processing fee."
    )

    # Status and Availability
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Media
    main_image = models.ImageField(upload_to='events/', blank=True, null=True)

    # Jersey-specific
    is_local_organiser = models.BooleanField(
        default=True,
        help_text="Is this a Jersey-based organiser?"
    )
    jersey_heritage = models.BooleanField(
        default=False,
        help_text="Does this event feature Jersey heritage/culture?"
    )

    # Metadata
    featured = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-event_date', '-event_time']

    def __str__(self):
        return f"{self.title} - {self.event_date}"

    def clean(self):
        """Validate event data before saving."""
        from events.validators import validate_event_capacity, validate_ticket_price

        # Validate capacity
        if self.capacity:
            validate_event_capacity(self.capacity)

        # Validate ticket price
        if self.ticket_price:
            validate_ticket_price(self.ticket_price)

    def save(self, *args, **kwargs):
        # Run clean validation
        self.clean()

        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        """Generate a unique slug for the event"""
        base_slug = slugify(f"{self.title}-{self.event_date}")
        slug = base_slug
        counter = 1

        # Check if slug exists and increment if needed
        while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def get_absolute_url(self):
        return reverse('events:detail', kwargs={'slug': self.slug})

    @property
    def is_sold_out(self):
        return self.tickets_sold >= self.capacity

    @property
    def tickets_available(self):
        return self.capacity - self.tickets_sold

    @property
    def total_revenue(self):
        return self.tickets_sold * self.ticket_price

    def get_pricing_tier(self):
        """
        Get the pricing tier for this event based on capacity.

        Returns:
            dict: Tier information (tier, capacity, fee, name)
            None: If capacity exceeds max or no tier found
        """
        from django.conf import settings
        return settings.get_pricing_tier(self.capacity)

    def get_platform_fee_per_ticket(self):
        """
        Calculate the platform fee per ticket based on event capacity.

        Returns:
            Decimal: Platform fee per ticket in GBP
            None: If capacity exceeds max supported capacity
        """
        tier = self.get_pricing_tier()
        if tier:
            return tier['fee']
        return None

    def get_processing_fee_per_ticket(self):
        """
        Calculate the SumUp processing fee per ticket (1.69% of ticket price).

        Returns:
            Decimal: Processing fee per ticket
        """
        from django.conf import settings
        return self.ticket_price * settings.SUMUP_PROCESSING_RATE

    def get_customer_ticket_price(self):
        """
        Calculate the final price the customer pays per ticket.

        Returns:
            Decimal: Final customer price including processing fee if passed through
        """
        if self.processing_fee_passed_to_customer:
            processing_fee = self.get_processing_fee_per_ticket()
            return self.ticket_price + processing_fee
        return self.ticket_price

    def get_organizer_net_per_ticket(self):
        """
        Calculate how much the organizer receives per ticket after all fees.

        Returns:
            Decimal: Net amount organizer receives per ticket
            None: If capacity exceeds max supported capacity
        """
        platform_fee = self.get_platform_fee_per_ticket()
        if platform_fee is None:
            return None

        processing_fee = self.get_processing_fee_per_ticket()

        if self.processing_fee_passed_to_customer:
            # Customer pays processing fee, organizer only pays platform fee
            return self.ticket_price - platform_fee
        else:
            # Organizer pays both platform fee and processing fee
            return self.ticket_price - platform_fee - processing_fee

    def get_fee_breakdown(self):
        """
        Get a complete breakdown of all fees and amounts.

        Returns:
            dict: Complete fee breakdown including all calculations
        """
        tier = self.get_pricing_tier()
        platform_fee = self.get_platform_fee_per_ticket()
        processing_fee = self.get_processing_fee_per_ticket()
        customer_price = self.get_customer_ticket_price()
        organizer_net = self.get_organizer_net_per_ticket()

        return {
            'tier': tier,
            'base_ticket_price': self.ticket_price,
            'platform_fee': platform_fee,
            'processing_fee': processing_fee,
            'processing_fee_passed_to_customer': self.processing_fee_passed_to_customer,
            'customer_pays': customer_price,
            'organizer_receives': organizer_net,
            'total_capacity': self.capacity,
            'tickets_sold': self.tickets_sold,
            'estimated_total_revenue': organizer_net * self.capacity if organizer_net else None,
        }


class Ticket(models.Model):
    """Individual ticket model."""
    STATUS_CHOICES = [
        ('valid', 'Valid'),
        ('used', 'Used'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tickets',
        limit_choices_to={'user_type': 'customer'}
    )
    ticket_tier = models.ForeignKey(
        'TicketTier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        help_text="Ticket tier (VIP, Standard, etc.). Null for legacy tickets."
    )
    ticket_number = models.CharField(max_length=20, unique=True)
    qr_code = models.ImageField(upload_to='tickets/qr_codes/', blank=True, null=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='valid'
    )

    # PDF ticket file
    pdf_file = models.FileField(
        upload_to='tickets/pdfs/',
        blank=True,
        null=True,
        help_text="Generated PDF ticket file"
    )

    # Validation fields
    validation_hash = models.CharField(
        max_length=32,
        blank=True,
        help_text="Unique validation hash for ticket verification"
    )
    qr_data = models.TextField(
        blank=True,
        help_text="QR code data for ticket validation"
    )
    is_validated = models.BooleanField(
        default=False,
        help_text="Whether this ticket has been used for entry"
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this ticket was validated for entry"
    )
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_tickets',
        help_text="Staff member who validated this ticket"
    )

    # Optional fields for additional ticket info
    seat_number = models.CharField(max_length=20, blank=True)
    special_requirements = models.TextField(blank=True)

    # Order relationship
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='tickets',
        null=True,
        blank=True,
        help_text="Order this ticket belongs to"
    )

    class Meta:
        ordering = ['-purchase_date']
        unique_together = ['event', 'ticket_number']

    def __str__(self):
        return f"Ticket {self.ticket_number} for {self.event.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()

        super().save(*args, **kwargs)

        # Generate QR code after saving
        if not self.qr_code:
            self.generate_qr_code()

    def generate_ticket_number(self):
        """Generate a unique ticket number."""
        return f"{self.event.slug[:10]}-{uuid.uuid4().hex[:8]}".upper()

    def generate_qr_code(self):
        """Generate QR code for the ticket."""
        # Use customer_email if customer is None
        customer_identifier = str(self.customer.id) if self.customer else self.customer_email
        qr_data = f"TICKET:{self.ticket_number}:EVENT:{self.event.slug}:CUSTOMER:{customer_identifier}"

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'ticket_{self.ticket_number}_qr.png'

        self.qr_code.save(filename, File(buffer), save=False)
        buffer.close()

        # Save again to update the qr_code field
        Ticket.objects.filter(pk=self.pk).update(qr_code=self.qr_code)

    def generate_pdf_ticket(self):
        """Generate PDF ticket with QR code and validation data."""
        try:
            from .ticket_generator import TicketGenerator
            from django.core.files.base import ContentFile

            generator = TicketGenerator()

            # Generate validation data
            self.validation_hash = generator.generate_ticket_validation_hash(self)
            self.qr_data = generator.generate_qr_code_data(self)

            # Generate PDF
            pdf_data = generator.generate_ticket_pdf(self)

            # Save PDF file
            filename = f"ticket_{self.ticket_number}.pdf"
            self.pdf_file.save(
                filename,
                ContentFile(pdf_data),
                save=False
            )

            # Update validation fields
            self.save(update_fields=['validation_hash', 'qr_data', 'pdf_file'])

            logger.info(f"Generated PDF ticket for {self.ticket_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate PDF ticket for {self.ticket_number}: {e}")
            return False

    def validate_ticket(self, validated_by=None):
        """Mark ticket as validated for entry."""
        if self.is_validated:
            return False, "Ticket has already been used"

        if self.status != 'valid':
            return False, f"Ticket is {self.status} and cannot be used"

        # Mark as validated
        self.is_validated = True
        self.validated_at = timezone.now()
        if validated_by:
            self.validated_by = validated_by

        self.save(update_fields=['is_validated', 'validated_at', 'validated_by'])

        logger.info(f"Ticket {self.ticket_number} validated for entry")
        return True, "Ticket validated successfully"

    def get_download_url(self):
        """Get URL for downloading the PDF ticket."""
        if self.pdf_file:
            return self.pdf_file.url
        return None

    @property
    def is_valid_for_entry(self):
        """Check if ticket is valid for entry."""
        return (
            self.status == 'valid' and
            not self.is_validated and
            self.event.event_date >= timezone.now().date()
        )


class TicketTier(models.Model):
    """Ticket tiers for events (VIP, Standard, Child, Concession, Elderly)."""
    TIER_TYPE_CHOICES = [
        ('standard', 'Standard'),
        ('vip', 'VIP'),
        ('child', 'Child'),
        ('concession', 'Concession'),
        ('elderly', 'Elderly/Senior'),
        ('student', 'Student'),
        ('group', 'Group'),
        ('earlybird', 'Early Bird'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='ticket_tiers'
    )
    tier_type = models.CharField(
        max_length=20,
        choices=TIER_TYPE_CHOICES,
        default='standard'
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for this tier (e.g., 'VIP Access', 'General Admission')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what's included in this tier"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base price for this tier"
    )
    quantity_available = models.PositiveIntegerField(
        help_text="Number of tickets available at this tier"
    )
    quantity_sold = models.PositiveIntegerField(
        default=0,
        help_text="Number of tickets sold at this tier"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this tier is available for purchase"
    )
    sort_order = models.IntegerField(
        default=0,
        help_text="Display order (lower numbers first)"
    )

    # Optional restrictions
    min_purchase = models.PositiveIntegerField(
        default=1,
        help_text="Minimum number of tickets per purchase"
    )
    max_purchase = models.PositiveIntegerField(
        default=10,
        help_text="Maximum number of tickets per purchase"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event', 'sort_order', 'tier_type']
        unique_together = ['event', 'tier_type']

    def __str__(self):
        return f"{self.name} - {self.event.title} (£{self.price})"

    def clean(self):
        """Validate ticket tier data before saving."""
        from events.validators import (
            validate_ticket_tier_capacity,
            validate_min_max_purchase,
            validate_ticket_price
        )

        # Validate tier capacity doesn't exceed event capacity
        if self.event_id and self.quantity_available:
            validate_ticket_tier_capacity(self.quantity_available, self.event.capacity)

        # Validate min/max purchase limits
        if self.min_purchase and self.max_purchase:
            validate_min_max_purchase(self.min_purchase, self.max_purchase)

        # Validate tier price
        if self.price:
            validate_ticket_price(self.price)

    def save(self, *args, **kwargs):
        # Run clean validation
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_sold_out(self):
        """Check if this tier is sold out."""
        return self.quantity_sold >= self.quantity_available

    @property
    def tickets_remaining(self):
        """Get number of tickets remaining for this tier."""
        return self.quantity_available - self.quantity_sold

    def get_customer_price(self):
        """
        Calculate the final price the customer pays for this tier.
        Includes processing fee if event has it enabled.

        Returns:
            Decimal: Final customer price
        """
        if self.event.processing_fee_passed_to_customer:
            from django.conf import settings
            processing_fee = self.price * settings.SUMUP_PROCESSING_RATE
            return self.price + processing_fee
        return self.price

    def reserve_tickets(self, quantity):
        """
        Reserve tickets from this tier (increment sold count).
        Must be called within a transaction.

        Args:
            quantity (int): Number of tickets to reserve

        Returns:
            bool: True if successful, False if not enough tickets
        """
        if self.tickets_remaining < quantity:
            logger.error(
                f"Not enough tickets in tier {self.id}: "
                f"requested={quantity}, available={self.tickets_remaining}"
            )
            return False

        self.quantity_sold += quantity
        self.save(update_fields=['quantity_sold'])
        logger.info(f"Reserved {quantity} tickets from tier {self.id}")
        return True


class EventFee(models.Model):
    """Model for charging organisers per event."""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ]

    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name='event_fee'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Fee charged to organiser for this event"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    due_date = models.DateField()
    paid_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return f"Fee for {self.event.title} - £{self.amount}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.payment_status == 'pending' and self.due_date < timezone.now().date()


class EventImage(models.Model):
    """Additional images for events."""
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='additional_images'
    )
    image = models.ImageField(upload_to='events/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"Image for {self.event.title}"


class EventView(models.Model):
    """Track event views for analytics."""
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='event_views'
    )
    viewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        return f"View of {self.event.title} at {self.viewed_at}"


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
        'Event',
        on_delete=models.CASCADE,
        related_name='listing_fee'
    )
    organizer = models.ForeignKey(
        User,
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
            import uuid
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