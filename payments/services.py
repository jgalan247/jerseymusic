import os
import requests
from decimal import Decimal
from django.conf import settings

class PaymentService:
    """Handle subscription payments."""
    
    def __init__(self):
        self.provider = settings.PAYMENT_PROVIDER
        self.api_key = settings.SUMUP_API_KEY
        self.merchant_id = settings.SUMUP_MERCHANT_ID
    
    def charge_subscription(self, subscription, amount):
        """Charge a subscription payment."""
        if self.provider == 'sumup':
            return self._charge_sumup(subscription, amount)
        elif self.provider == 'stripe':
            return self._charge_stripe(subscription, amount)
        else:
            # Test mode
            return {'success': True, 'transaction_id': 'TEST_' + str(subscription.id)}
    
    def _charge_sumup(self, subscription, amount):
        """Process payment via SumUp."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'checkout_reference': f'SUB_{subscription.id}',
            'amount': float(amount),
            'currency': subscription.currency,
            'description': f'Jersey Artwork Monthly Subscription',
            'merchant_code': self.merchant_id,
        }
        
        try:
            response = requests.post(
                f"{settings.SUMUP_API_URL}/checkouts",
                json=data,
                headers=headers
            )
            
            if response.status_code == 201:
                result = response.json()
                return {
                    'success': True,
                    'transaction_id': result.get('id'),
                    'checkout_url': result.get('checkout_url')
                }
            else:
                return {
                    'success': False,
                    'error': response.text
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }