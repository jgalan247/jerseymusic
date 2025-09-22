from django.db import models
from django.conf import settings
from accounts.models import User
from artworks.models import Artwork
from decimal import Decimal


class Cart(models.Model):
    """Shopping cart model."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts'
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text="For anonymous users"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Anonymous cart ({self.session_key[:8]}...)"

    @property
    def total_items(self):
        """Get total number of items in cart."""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

    @property
    def subtotal(self):
        """Calculate cart subtotal."""
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.total_price
        return total

    @property
    def shipping_cost(self):
        """Calculate shipping cost."""
        # Jersey is small, fixed shipping rate
        if self.subtotal > Decimal('100.00'):
            return Decimal('0.00')  # Free shipping over £100
        return Decimal('5.00')  # Fixed £5 shipping

    @property
    def total(self):
        """Calculate cart total including shipping."""
        return self.subtotal + self.shipping_cost

    def clear(self):
        """Clear all items from cart."""
        self.items.all().delete()

    def merge_with(self, other_cart):
        """Merge another cart into this one (useful after login)."""
        for item in other_cart.items.all():
            existing_item = self.items.filter(artwork=item.artwork).first()
            if existing_item:
                existing_item.quantity += item.quantity
                existing_item.save()
            else:
                item.cart = self
                item.save()
        other_cart.delete()


class CartItem(models.Model):
    """Individual item in a cart."""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    artwork = models.ForeignKey(
        Artwork,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price_at_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price when added to cart"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = ['cart', 'artwork']

    def __str__(self):
        return f"{self.quantity}x {self.artwork.title}"

    def save(self, *args, **kwargs):
        # Set price when item is first added
        if not self.pk and not self.price_at_time:
            self.price_at_time = self.artwork.price
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        """Calculate total price for this line item."""
        return Decimal(str(self.quantity)) * self.price_at_time

    @property
    def is_available(self):
        """Check if artwork is still available."""
        if self.artwork.artwork_type == 'original':
            return self.artwork.is_available and self.artwork.stock_quantity > 0
        else:  # Prints can have multiple quantity
            return self.artwork.is_available and self.artwork.stock_quantity >= self.quantity


class SavedItem(models.Model):
    """Items saved for later (wishlist)."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_items'
    )
    artwork = models.ForeignKey(
        Artwork,
        on_delete=models.CASCADE
    )
    added_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = ['user', 'artwork']

    def __str__(self):
        return f"{self.user.username} saved {self.artwork.title}"
