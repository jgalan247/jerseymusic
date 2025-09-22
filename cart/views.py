from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import F
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from decimal import Decimal

from .models import Cart, CartItem, SavedItem
from artworks.models import Artwork


class CartView(TemplateView):
    """Display shopping cart."""
    template_name = 'cart/view.html'
    
    def get_cart(self):
        """Get or create cart for current user/session."""
        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(
                user=self.request.user,
                is_active=True
            )
        else:
            # For anonymous users, use session
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                is_active=True
            )
        
        return cart
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.get_cart()
        
        # Get cart items with related artwork data
        cart_items = cart.items.select_related(
            'artwork', 
            'artwork__artist'
        ).order_by('-added_at')
        
        # Check availability for each item - IMPORTANT: Check this happens every time
        has_unavailable = False
        for item in cart_items:
            # Check both is_available flag and stock quantity
            if not item.artwork.is_available or item.artwork.stock_quantity == 0:
                messages.warning(
                    self.request, 
                    f"{item.artwork.title} is no longer available"
                )
                item.available = False
                has_unavailable = True
            elif item.quantity > item.artwork.stock_quantity:
                messages.warning(
                    self.request, 
                    f"{item.artwork.title} is no longer available in the requested quantity."
                )
                item.available = False
                has_unavailable = True
            else:
                item.available = True
        
        context['cart'] = cart
        context['cart_items'] = cart_items
        context['has_unavailable'] = has_unavailable  # Add this for template use if needed
        
        # Get saved items if user is authenticated
        if self.request.user.is_authenticated:
            context['saved_items'] = SavedItem.objects.filter(
                user=self.request.user
            ).select_related('artwork')
        
        return context


class AddToCartView(View):
    """Add artwork to cart."""
    
    def post(self, request, artwork_id):
        artwork = get_object_or_404(Artwork, id=artwork_id, status='active')
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity < 1:
            messages.error(request, "Invalid quantity.")
            return redirect('artworks:artwork_detail', pk=artwork.id)
        
        # Check availability
        # Check if artwork is available at all
        if not artwork.is_available:
            messages.error(request, "This artwork is not available.")
            return redirect('artworks:artwork_detail', pk=artwork.id)

        # Check stock quantity
        if quantity > artwork.stock_quantity:
            messages.error(request, f"Only {artwork.stock_quantity} available.")
            return redirect('artworks:artwork_detail', pk=artwork.id)
        # Get or create cart
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(
                user=request.user,
                is_active=True
            )
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                is_active=True
            )
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            artwork=artwork,
            defaults={
                'quantity': quantity,
                'price_at_time': artwork.price
            }
        )
        
        if not created:
            # Update quantity if item already in cart
            cart_item.quantity = F('quantity') + quantity
            cart_item.save()
            cart_item.refresh_from_db()
            
            # Check if updated quantity is available
            if cart_item.quantity > artwork.stock_quantity:
                cart_item.quantity = artwork.stock_quantity
                cart_item.save()
                messages.warning(
                    request, 
                    f"Quantity adjusted to {artwork.stock_quantity} (maximum available)."
                )
            else:
                messages.success(request, f"Updated quantity to {cart_item.quantity}.")
        else:
            messages.success(request, f"Added {artwork.title} to cart.")
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_total_items': cart.total_items,
                'message': f"Added to cart successfully."
            })
        
        return redirect('cart:view')


class UpdateCartItemView(View):
    """Update cart item quantity."""
    
    def post(self, request, item_id):
    # Get cart
        if request.user.is_authenticated:
            cart = Cart.objects.filter(
                user=request.user,
                is_active=True
            ).first()
        else:
            session_key = request.session.session_key
            cart = Cart.objects.filter(
                session_key=session_key,
                is_active=True
            ).first()
        
        if not cart:
            messages.error(request, "Cart not found.")
            return redirect('cart:view')
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity < 1:
            # If quantity is 0 or negative, remove item
            cart_item.delete()
            messages.success(request, "Item removed from cart.")
        else:
            # Check availability and adjust if needed
            if quantity > cart_item.artwork.stock_quantity:
                quantity = cart_item.artwork.stock_quantity
                cart_item.quantity = quantity
                cart_item.save()
                messages.warning(
                    request,
                    f"Quantity adjusted to {quantity} (maximum available)."
                )
            else:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, "Cart updated.")
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'item_total': str(cart_item.total_price) if quantity > 0 else "0.00",
                'cart_subtotal': str(cart.subtotal),
                'cart_total': str(cart.total),
                'cart_total_items': cart.total_items
            })
        
        return redirect('cart:view')


class RemoveFromCartView(View):
    """Remove item from cart."""
    
    def post(self, request, item_id):
        # Get cart
        if request.user.is_authenticated:
            cart = Cart.objects.filter(
                user=request.user,
                is_active=True
            ).first()
        else:
            session_key = request.session.session_key
            cart = Cart.objects.filter(
                session_key=session_key,
                is_active=True
            ).first()
        
        if not cart:
            messages.error(request, "Cart not found.")
            return redirect('cart:view')
        
        # Remove item
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        artwork_title = cart_item.artwork.title
        cart_item.delete()
        
        messages.success(request, f"Removed {artwork_title} from cart.")
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_subtotal': str(cart.subtotal),
                'cart_total': str(cart.total),
                'cart_total_items': cart.total_items
            })
        
        return redirect('cart:view')


class ClearCartView(View):
    """Clear all items from cart."""
    
    def post(self, request):
        # Get cart
        if request.user.is_authenticated:
            cart = Cart.objects.filter(
                user=request.user,
                is_active=True
            ).first()
        else:
            session_key = request.session.session_key
            cart = Cart.objects.filter(
                session_key=session_key,
                is_active=True
            ).first()
        
        if cart:
            cart.clear()
            messages.success(request, "Cart cleared.")
        
        return redirect('cart:view')


@method_decorator(login_required, name='dispatch')
class SaveForLaterView(View):
    """Save item for later (wishlist)."""
    
    def post(self, request, artwork_id):
        artwork = get_object_or_404(Artwork, id=artwork_id)
        
        saved_item, created = SavedItem.objects.get_or_create(
            user=request.user,
            artwork=artwork
        )
        
        if created:
            messages.success(request, f"Saved {artwork.title} for later.")
            
            # Remove from cart if it exists
            cart = Cart.objects.filter(user=request.user, is_active=True).first()
            if cart:
                CartItem.objects.filter(cart=cart, artwork=artwork).delete()
        else:
            messages.info(request, "Item already saved.")
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'saved': created
            })
        
        return redirect('cart:view')


@method_decorator(login_required, name='dispatch')
class MoveToCartView(View):
    """Move saved item back to cart."""
    
    def post(self, request, item_id):
        saved_item = get_object_or_404(SavedItem, id=item_id, user=request.user)
        artwork = saved_item.artwork
        
        # Check availability
        if not artwork.is_available:
            messages.error(request, f"{artwork.title} is no longer available.")
            return redirect('cart:view')
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True
        )
        
        # Add to cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            artwork=artwork,
            defaults={
                'quantity': 1,
                'price_at_time': artwork.price
            }
        )
        
        if not created:
            cart_item.quantity = F('quantity') + 1
            cart_item.save()
        
        # Remove from saved items
        saved_item.delete()
        
        messages.success(request, f"Moved {artwork.title} to cart.")
        
        return redirect('cart:view')