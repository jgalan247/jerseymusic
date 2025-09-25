from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from accounts.models import User
from decimal import Decimal
import uuid
import qrcode
from io import BytesIO
from django.core.files import File


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
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


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
    capacity = models.PositiveIntegerField()
    tickets_sold = models.PositiveIntegerField(default=0)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)

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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.event_date}")
        super().save(*args, **kwargs)

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
    ticket_number = models.CharField(max_length=20, unique=True)
    qr_code = models.ImageField(upload_to='tickets/qr_codes/', blank=True, null=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='valid'
    )

    # Optional fields for additional ticket info
    seat_number = models.CharField(max_length=20, blank=True)
    special_requirements = models.TextField(blank=True)

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