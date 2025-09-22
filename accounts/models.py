from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse

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
    def total_artworks(self):
        """Return total number of artworks by this artist."""
        return self.user.artworks.count()
    
    @property
    def active_artworks(self):
        """Return number of active artworks."""
        return self.user.artworks.filter(status='active').count()
