"""
Order and Checkout Validation
==============================
Validators for order processing, T&C acceptance, and checkout flow.
"""

from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone


def validate_terms_acceptance(terms_accepted, terms_version=None):
    """
    Validate that Terms & Conditions have been accepted.

    Args:
        terms_accepted (bool): Whether T&C were accepted
        terms_version (str, optional): Version of T&C accepted

    Raises:
        ValidationError: If T&C not accepted
    """
    if not terms_accepted:
        raise ValidationError(
            'You must accept the Terms & Conditions to complete your purchase. '
            'Please read and check the agreement box.'
        )

    # Validate T&C version if provided
    if terms_version and terms_version != settings.TERMS_VERSION:
        raise ValidationError(
            f'Terms & Conditions version mismatch. Please refresh the page and '
            f'review the current Terms & Conditions (Version {settings.TERMS_VERSION}).'
        )


def validate_order_email(email):
    """
    Validate order email address format and requirements.

    Args:
        email (str): Email address

    Raises:
        ValidationError: If email is invalid
    """
    if not email or '@' not in email:
        raise ValidationError('A valid email address is required to receive your tickets.')

    # Check for common typos in popular email domains
    common_typos = {
        'gmail.con': 'gmail.com',
        'gmail.co': 'gmail.com',
        'gmial.com': 'gmail.com',
        'gmai.com': 'gmail.com',
        'hotmail.con': 'hotmail.com',
        'hotmail.co': 'hotmail.com',
        'yahoo.con': 'yahoo.com',
        'yahoo.co': 'yahoo.com',
    }

    domain = email.split('@')[1].lower() if '@' in email else ''
    if domain in common_typos:
        raise ValidationError(
            f'Did you mean {email.split("@")[0]}@{common_typos[domain]}? '
            f'Please check your email address carefully as tickets will be sent there.'
        )


def validate_order_phone(phone):
    """
    Validate phone number format.

    Args:
        phone (str): Phone number

    Raises:
        ValidationError: If phone is invalid
    """
    if not phone:
        raise ValidationError('Phone number is required.')

    # Remove common formatting characters
    digits = ''.join(filter(str.isdigit, phone))

    if len(digits) < 6:
        raise ValidationError('Phone number seems too short. Please enter a valid phone number.')

    if len(digits) > 15:
        raise ValidationError('Phone number seems too long. Please enter a valid phone number.')


def validate_ticket_availability(cart_items):
    """
    Validate all tickets in cart are still available.

    Args:
        cart_items: QuerySet or list of CartItem objects

    Raises:
        ValidationError: If tickets are not available
    """
    unavailable_items = []

    for item in cart_items:
        event = item.event

        # Check if event is still published
        if event.status != 'published':
            unavailable_items.append(
                f'{event.title}: Event is no longer available (Status: {event.get_status_display()})'
            )
            continue

        # Check if tickets are available
        if event.tickets_available < item.quantity:
            unavailable_items.append(
                f'{event.title}: Only {event.tickets_available} tickets remaining, '
                f'but you requested {item.quantity}'
            )

    if unavailable_items:
        raise ValidationError(
            'Some items in your cart are no longer available:\n' +
            '\n'.join(f'• {item}' for item in unavailable_items)
        )


def validate_tier_availability(tier, quantity):
    """
    Validate ticket tier has enough capacity for requested quantity.

    Args:
        tier: TicketTier instance
        quantity (int): Requested quantity

    Raises:
        ValidationError: If tier doesn't have enough tickets
    """
    if not tier.is_active:
        raise ValidationError(
            f'The {tier.name} tier is no longer available for purchase.'
        )

    if tier.tickets_remaining < quantity:
        if tier.tickets_remaining == 0:
            raise ValidationError(
                f'{tier.name} tickets are sold out. '
                f'Please select a different tier or reduce your quantity.'
            )
        else:
            raise ValidationError(
                f'Only {tier.tickets_remaining} {tier.name} tickets remaining. '
                f'You requested {quantity}. Please reduce your quantity.'
            )

    # Validate min/max purchase limits
    if quantity < tier.min_purchase:
        raise ValidationError(
            f'{tier.name} requires a minimum purchase of {tier.min_purchase} tickets. '
            f'You selected {quantity}.'
        )

    if quantity > tier.max_purchase:
        raise ValidationError(
            f'{tier.name} has a maximum purchase limit of {tier.max_purchase} tickets. '
            f'You selected {quantity}. For bulk purchases, please contact support.'
        )


def validate_checkout_data(data, cart):
    """
    Comprehensive validation of checkout form data.

    Args:
        data (dict): Cleaned form data
        cart: Cart instance

    Raises:
        ValidationError: If any validation fails
    """
    errors = []

    # Validate required fields
    required_fields = ['first_name', 'last_name', 'email', 'phone']
    for field in required_fields:
        if not data.get(field):
            errors.append(f'{field.replace("_", " ").title()} is required.')

    # Validate T&C acceptance
    if not data.get('terms_accepted'):
        errors.append('You must accept the Terms & Conditions to complete your purchase.')

    # Validate cart not empty
    if not cart or cart.total_items == 0:
        errors.append('Your cart is empty. Please add tickets before checking out.')

    # Validate email format
    try:
        validate_order_email(data.get('email', ''))
    except ValidationError as e:
        errors.append(str(e.message))

    # Validate phone
    try:
        validate_order_phone(data.get('phone', ''))
    except ValidationError as e:
        errors.append(str(e.message))

    # Validate ticket availability
    try:
        validate_ticket_availability(cart.items.all())
    except ValidationError as e:
        errors.append(str(e.message))

    if errors:
        raise ValidationError(errors)

    return True


def get_client_ip(request):
    """
    Get client IP address from request, handling proxies.

    Args:
        request: Django request object

    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get first IP in chain (client IP)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    return ip


def record_terms_acceptance(order, request):
    """
    Record Terms & Conditions acceptance with legal metadata.

    Args:
        order: Order instance
        request: Django request object

    Returns:
        Order: Updated order instance
    """
    order.terms_accepted = True
    order.terms_accepted_at = timezone.now()
    order.terms_version = settings.TERMS_VERSION
    order.acceptance_ip = get_client_ip(request)
    order.save(update_fields=['terms_accepted', 'terms_accepted_at', 'terms_version', 'acceptance_ip'])

    return order


class TermsAcceptanceValidator:
    """Custom validator for T&C acceptance."""

    message = 'You must accept the Terms & Conditions.'
    code = 'terms_not_accepted'

    def __call__(self, value):
        if not value:
            raise ValidationError(self.message, code=self.code)


class TicketAvailabilityValidator:
    """Custom validator for ticket availability."""

    message = 'Tickets are not available.'
    code = 'tickets_unavailable'

    def __init__(self, event):
        self.event = event

    def __call__(self, quantity):
        if quantity > self.event.tickets_available:
            raise ValidationError(
                f'Only {self.event.tickets_available} tickets available. You requested {quantity}.',
                code=self.code
            )
