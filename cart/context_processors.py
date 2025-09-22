from .models import Cart


def cart_context(request):
    """Make cart available in all templates."""
    cart = None
    
    if request.user.is_authenticated:
        cart = Cart.objects.filter(
            user=request.user,
            is_active=True
        ).first()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(
                session_key=session_key,
                is_active=True
            ).first()
    
    return {
        'cart': cart if cart else None
    }
