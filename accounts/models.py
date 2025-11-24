from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.urls import reverse
import uuid
from django.utils import timezone
from datetime import timedelta

class UserManager(BaseUserManager):
    """Custom user manager for email-only authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Extended user model with email-only authentication."""
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('artist', 'Artist'),
    ]

    # Remove username field
    username = None

    # Make email the unique identifier
    email = models.EmailField(unique=True, verbose_name='Email Address')

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='customer'
    )
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)

    # Set email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    # Use custom manager
    objects = UserManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip() or self.email

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
    address_line_2 = models.CharField(max_length=255, blank=True)
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
    phone_number = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Customer"
    
    def get_absolute_url(self):
        return reverse('accounts:profile')

class ArtistProfile(Profile):
    """Artist profile following Django naming conventions."""
    display_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    business_name = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
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

    # SumUp OAuth integration
    sumup_access_token = models.TextField(
        blank=True,
        help_text="SumUp OAuth access token for this artist"
    )
    sumup_refresh_token = models.TextField(
        blank=True,
        help_text="SumUp OAuth refresh token"
    )
    sumup_token_type = models.CharField(
        max_length=20,
        default='Bearer',
        blank=True
    )
    sumup_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the access token expires"
    )
    sumup_scope = models.CharField(
        max_length=255,
        blank=True,
        help_text="OAuth scopes granted"
    )
    sumup_merchant_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Artist's SumUp merchant code"
    )
    sumup_connected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When SumUp was first connected"
    )
    sumup_connection_status = models.CharField(
        max_length=20,
        choices=[
            ('not_connected', 'Not Connected'),
            ('connected', 'Connected'),
            ('expired', 'Token Expired'),
            ('error', 'Connection Error'),
        ],
        default='not_connected',
        help_text="Current SumUp connection status"
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

    @property
    def is_sumup_connected(self):
        """Check if artist has valid SumUp connection."""
        return (
            self.sumup_connection_status == 'connected' and
            self.sumup_access_token and
            self.sumup_merchant_code
        )

    @property
    def sumup_token_expired(self):
        """Check if SumUp token has expired."""
        if not self.sumup_expires_at:
            return False
        return timezone.now() > self.sumup_expires_at

    def update_sumup_connection(self, token_data):
        """Update SumUp OAuth tokens and connection status."""
        self.sumup_access_token = token_data.get('access_token', '')
        self.sumup_refresh_token = token_data.get('refresh_token', '')
        self.sumup_token_type = token_data.get('token_type', 'Bearer')
        self.sumup_scope = token_data.get('scope', '')
        self.sumup_merchant_code = token_data.get('merchant_code', '')

        # Set expiration time - handle both expires_at (datetime) and expires_in (seconds)
        if 'expires_at' in token_data:
            # Token data contains pre-calculated expiration datetime
            self.sumup_expires_at = token_data['expires_at']
        elif 'expires_in' in token_data:
            # Token data contains seconds until expiration
            from django.utils import timezone
            from datetime import timedelta
            expires_in = int(token_data['expires_in'])
            self.sumup_expires_at = timezone.now() + timedelta(seconds=expires_in - 30)

        # Update connection status and timestamp
        self.sumup_connection_status = 'connected'
        if not self.sumup_connected_at:
            self.sumup_connected_at = timezone.now()

        self.save()

    def disconnect_sumup(self):
        """Disconnect SumUp integration."""
        self.sumup_access_token = ''
        self.sumup_refresh_token = ''
        self.sumup_token_type = ''
        self.sumup_expires_at = None
        self.sumup_scope = ''
        self.sumup_merchant_code = ''
        self.sumup_connection_status = 'not_connected'
        self.save()


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
