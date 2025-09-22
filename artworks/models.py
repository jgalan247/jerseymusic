from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from accounts.models import User  # Import your custom User model
from decimal import Decimal


class Category(models.Model):
    """Categories for organizing artworks."""
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


class Artwork(models.Model):
    """Main artwork model."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('sold', 'Sold'),
        ('reserved', 'Reserved'),
        ('archived', 'Archived'),
    ]
    
    ARTWORK_TYPE_CHOICES = [
        ('original', 'Original'),
        ('print', 'Print'),
        ('digital', 'Digital Print'),
        ('commission', 'Commission'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    artist = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='artworks',
        limit_choices_to={'user_type': 'artist'}
    )
    
    # Artwork Details
    description = models.TextField()
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='artworks'
    )
    artwork_type = models.CharField(
        max_length=20, 
        choices=ARTWORK_TYPE_CHOICES,
        default='original'
    )
    
    # Physical Attributes
    height = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        help_text="Height in cm",
        null=True,
        blank=True
    )
    width = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        help_text="Width in cm",
        null=True,
        blank=True
    )
    depth = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        help_text="Depth in cm (for sculptures)",
        null=True,
        blank=True
    )
    materials = models.CharField(max_length=200, blank=True)
    year_created = models.IntegerField(null=True, blank=True)
    
    # Pricing and Availability
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    stock_quantity = models.IntegerField(
        default=1,
        help_text="For prints or reproductions"
    )
    
    # Media
    main_image = models.ImageField(upload_to='artworks/')
    
    # Jersey-specific
    is_local_artist = models.BooleanField(
        default=True,
        help_text="Is this a Jersey-based artist?"
    )
    jersey_heritage = models.BooleanField(
        default=False,
        help_text="Does this artwork depict Jersey heritage/culture?"
    )
    
    # Metadata
    featured = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.artist.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.artist.username}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('artworks:detail', kwargs={'slug': self.slug})

    @property
    def is_sold(self):
        return self.status == 'sold'

    @property
    def dimensions(self):
        """Return formatted dimensions string."""
        dims = []
        if self.height:
            dims.append(f"H: {self.height}cm")
        if self.width:
            dims.append(f"W: {self.width}cm")
        if self.depth:
            dims.append(f"D: {self.depth}cm")
        return " × ".join(dims) if dims else "Dimensions not specified"


class ArtworkImage(models.Model):
    """Additional images for artworks."""
    artwork = models.ForeignKey(
        Artwork,
        on_delete=models.CASCADE,
        related_name='additional_images'
    )
    image = models.ImageField(upload_to='artworks/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"Image for {self.artwork.title}"


class ArtworkView(models.Model):
    """Track artwork views for analytics."""
    artwork = models.ForeignKey(
        Artwork,
        on_delete=models.CASCADE,
        related_name='artwork_views'
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
        return f"View of {self.artwork.title} at {self.viewed_at}"
