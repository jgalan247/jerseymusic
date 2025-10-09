"""
Event and Ticket Validation
============================
Validators for event creation, capacity limits, and ticket tiers.
"""

from django.core.exceptions import ValidationError
from django.conf import settings
from decimal import Decimal


def validate_event_capacity(capacity):
    """
    Validate event capacity is within allowed limits.

    Args:
        capacity (int): Event capacity

    Raises:
        ValidationError: If capacity exceeds maximum or is invalid
    """
    if capacity <= 0:
        raise ValidationError('Event capacity must be greater than zero.')

    if capacity > settings.MAX_AUTO_CAPACITY:
        raise ValidationError(
            f'Maximum capacity for automatic pricing is {settings.MAX_AUTO_CAPACITY} tickets. '
            f'For events larger than {settings.MAX_AUTO_CAPACITY}, please contact '
            f'{settings.CUSTOM_PRICING_EMAIL} for custom pricing options.'
        )


def validate_ticket_price(price):
    """
    Validate ticket price is reasonable.

    Args:
        price (Decimal): Ticket price

    Raises:
        ValidationError: If price is invalid
    """
    if price <= Decimal('0'):
        raise ValidationError('Ticket price must be greater than zero.')

    if price > Decimal('10000.00'):
        raise ValidationError(
            'Ticket price seems unusually high. Maximum allowed is £10,000. '
            'Please contact support if you need to set a higher price.'
        )


def validate_ticket_tier_capacity(tier_capacity, event_capacity):
    """
    Validate ticket tier capacity doesn't exceed event capacity.

    Args:
        tier_capacity (int): Capacity for this ticket tier
        event_capacity (int): Total event capacity

    Raises:
        ValidationError: If tier capacity exceeds event capacity
    """
    if tier_capacity <= 0:
        raise ValidationError('Ticket tier capacity must be greater than zero.')

    if tier_capacity > event_capacity:
        raise ValidationError(
            f'Ticket tier capacity ({tier_capacity}) cannot exceed '
            f'total event capacity ({event_capacity}).'
        )


def validate_tier_price_range(tier_price, base_price):
    """
    Validate ticket tier price is reasonable relative to base price.

    Args:
        tier_price (Decimal): Price for this tier
        base_price (Decimal): Base event ticket price

    Raises:
        ValidationError: If tier price is unreasonably high/low
    """
    if tier_price <= Decimal('0'):
        raise ValidationError('Ticket tier price must be greater than zero.')

    # Allow tier prices to be up to 10x base price (for VIP tiers)
    if tier_price > base_price * 10:
        raise ValidationError(
            f'Tier price (£{tier_price}) seems unusually high compared to '
            f'base price (£{base_price}). Maximum suggested is £{base_price * 10}.'
        )

    # Child/Concession tiers shouldn't be more expensive than base
    tier_type = getattr(tier_price, '_tier_type', None)
    if tier_type in ['child', 'concession', 'elderly', 'student']:
        if tier_price > base_price:
            raise ValidationError(
                f'{tier_type.title()} tier price (£{tier_price}) should not exceed '
                f'standard price (£{base_price}).'
            )


def validate_min_max_purchase(min_purchase, max_purchase):
    """
    Validate min/max purchase limits are sensible.

    Args:
        min_purchase (int): Minimum tickets per purchase
        max_purchase (int): Maximum tickets per purchase

    Raises:
        ValidationError: If limits are invalid
    """
    if min_purchase < 1:
        raise ValidationError('Minimum purchase must be at least 1 ticket.')

    if max_purchase < min_purchase:
        raise ValidationError(
            f'Maximum purchase ({max_purchase}) must be greater than or equal to '
            f'minimum purchase ({min_purchase}).'
        )

    if max_purchase > 100:
        raise ValidationError(
            'Maximum purchase limit cannot exceed 100 tickets per transaction. '
            'Contact support for bulk purchase arrangements.'
        )


def validate_tier_quantities(event):
    """
    Validate total tier quantities don't exceed event capacity.

    Args:
        event: Event instance with ticket_tiers

    Raises:
        ValidationError: If total tier capacity exceeds event capacity
    """
    from events.models import TicketTier
    from django.db.models import Sum

    total_tier_capacity = TicketTier.objects.filter(
        event=event,
        is_active=True
    ).aggregate(
        total=Sum('quantity_available')
    )['total'] or 0

    if total_tier_capacity > event.capacity:
        raise ValidationError(
            f'Total ticket tier capacity ({total_tier_capacity}) exceeds '
            f'event capacity ({event.capacity}). Please adjust tier quantities.'
        )


def validate_processing_fee_configuration(event):
    """
    Validate processing fee configuration is valid.

    Args:
        event: Event instance

    Returns:
        dict: Warning messages if any
    """
    warnings = []

    # Calculate the impact of passing fee to customer
    processing_fee_per_ticket = event.get_processing_fee_per_ticket()

    if event.processing_fee_passed_to_customer:
        # Warn if processing fee adds significant cost
        if processing_fee_per_ticket > event.ticket_price * Decimal('0.05'):  # More than 5%
            warnings.append(
                f'Processing fee (£{processing_fee_per_ticket:.2f}) adds '
                f'{(processing_fee_per_ticket / event.ticket_price * 100):.1f}% to ticket price. '
                f'Consider absorbing this cost to keep prices competitive.'
            )

    return warnings


class EventCapacityValidator:
    """Custom validator for event capacity field."""

    message = 'Event capacity exceeds maximum allowed.'
    code = 'invalid_capacity'

    def __call__(self, value):
        validate_event_capacity(value)


class TicketPriceValidator:
    """Custom validator for ticket price field."""

    message = 'Invalid ticket price.'
    code = 'invalid_price'

    def __call__(self, value):
        validate_ticket_price(value)
