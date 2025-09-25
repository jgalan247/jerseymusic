from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
import uuid
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    """Extended user model following Django conventions."""
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('artist', 'Artist'),
    ]
    
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPE_CHOICES, 
        default='customer'
    )
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()

class Profile(models.Model):
    """Base profile model - Django convention for extending User."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class CustomerProfile(Profile):
    """Customer profile following Django naming conventions."""
    date_of_birth = models.DateField(null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)
    
    # Jersey-specific fields
    address_line_1 = models.CharField(max_length=255, blank=True)
    parish = models.CharField(max_length=50, blank=True, choices=[
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
    postcode = models.CharField(max_length=10, blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Customer"
    
    def get_absolute_url(self):
        return reverse('accounts:profile')

class ArtistProfile(Profile):
    """Artist profile following Django naming conventions."""
    display_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    business_name = models.CharField(max_length=200, blank=True)  # Add this
    phone_number = models.CharField(max_length=20, blank=True)  # Add this
    website = models.URLField(blank=True)
    instagram_handle = models.CharField(max_length=100, blank=True)
    studio_address = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=15.00,
        help_text="Commission percentage for pay-per-sale"
    )
    
    def __str__(self):
        return f"{self.display_name} - Artist"
    
    def get_absolute_url(self):
        return reverse('accounts:artist_profile', kwargs={'pk': self.pk})
    
    @property
    def total_events(self):
        """Return total number of events by this organiser."""
        return self.user.events.count()
    
    @property
    def active_events(self):
        """Return number of published events."""
        return self.user.events.filter(status='published').count()


class EmailVerificationToken(models.Model):
    """Token model for email verification."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='verification_tokens'
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Verification token for {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Set expiration to 24 hours from creation
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired

    def mark_as_used(self):
        """Mark token as used and save."""
        self.is_used = True
        self.save()

    @classmethod
    def create_for_user(cls, user):
        """Create a new verification token for user and invalidate old ones."""
        # Invalidate existing tokens for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        # Create new token
        return cls.objects.create(user=user)
