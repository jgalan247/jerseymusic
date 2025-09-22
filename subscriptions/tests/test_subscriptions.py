from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from subscriptions.models import Subscription, SubscriptionPayment

class SubscriptionModelTests(TestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username='artist@test.com',
            email='artist@test.com',
            password='test123',
            user_type='artist'
        )
    
    def test_create_subscription(self):
        """Test creating artist subscription"""
        sub = Subscription.objects.create(
            user=self.artist,
            status='active'
        )
        self.assertEqual(sub.monthly_price, Decimal('15.00'))
        self.assertTrue(sub.is_active)
    
    def test_trial_period(self):
        """Test trial period setup"""
        sub = Subscription.objects.create(
            user=self.artist,
            status='trialing'
        )
        self.assertIsNotNone(sub.trial_end)
        self.assertEqual(sub.status, 'trialing')
    
    def test_subscription_cancellation(self):
        """Test cancelling subscription"""
        sub = Subscription.objects.create(
            user=self.artist,
            status='active'
        )
        sub.cancel()
        self.assertIsNotNone(sub.cancelled_at)
    
    def test_is_active_property(self):
        """Test is_active property for different statuses"""
        # Active should be active
        sub = Subscription.objects.create(
            user=self.artist,
            status='active'
        )
        self.assertTrue(sub.is_active)
        
        # Trial should be active
        sub.status = 'trialing'
        self.assertTrue(sub.is_active)
        
        # Cancelled should not be active
        sub.status = 'cancelled'
        self.assertFalse(sub.is_active)

class SubscriptionPaymentTests(TestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username='artist@test.com',
            email='artist@test.com',
            password='test123',
            user_type='artist'
        )
        self.subscription = Subscription.objects.create(
            user=self.artist,
            status='active'
        )
    
    def test_payment_creation(self):
        """Test creating subscription payment"""
        payment = SubscriptionPayment.objects.create(
            subscription=self.subscription,
            amount=Decimal('15.00'),
            currency='GBP',
            status='succeeded'
        )
        self.assertEqual(payment.amount, Decimal('15.00'))
        self.assertEqual(payment.subscription, self.subscription)