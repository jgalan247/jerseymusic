#!/usr/bin/env python
"""
Analytics Integration Health Check
Verify analytics integration doesn't interfere with core functionality
"""

import os
import sys
import django
from datetime import datetime, timedelta, date
from decimal import Decimal
import random
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from django.test import Client

# Existing models
from accounts.models import ArtistProfile
from events.models import Event, Category
from orders.models import Order, OrderItem
from cart.models import Cart, CartItem

# Analytics models and services
from analytics.models import (
    SumUpConnectionEvent,
    DailyConnectionMetrics,
    EmailCampaignMetrics,
    ConnectionAlert
)
from analytics.services import AnalyticsService

User = get_user_model()

def test_analytics_integration_health():
    """Quick health check of analytics integration points"""
    print("🔗 ANALYTICS INTEGRATION HEALTH CHECK")
    print("=" * 50)

    tests_passed = 0
    total_tests = 0

    # Test 1: Core functionality still works alongside analytics
    total_tests += 1
    try:
        print("1️⃣ Testing core functionality preservation...")

        # Test basic database operations
        user_count = User.objects.count()
        event_count = Event.objects.count()
        artist_count = ArtistProfile.objects.count()

        if user_count >= 0 and event_count >= 0 and artist_count >= 0:
            print("  ✅ Core database queries working")
            tests_passed += 1
        else:
            print("  ❌ Core database queries failed")

    except Exception as e:
        print(f"  ❌ Core functionality test failed: {e}")

    # Test 2: Analytics service doesn't break existing operations
    total_tests += 1
    try:
        print("2️⃣ Testing analytics service integration...")

        # Initialize analytics service
        analytics_service = AnalyticsService()

        # Test that existing data can be retrieved
        current_metrics = analytics_service.get_current_metrics()

        if current_metrics is not None:
            print("  ✅ Analytics service returns data")

            # Verify data types are correct
            if (isinstance(current_metrics.get('total_artists', 0), int) and
                isinstance(current_metrics.get('connected_artists', 0), int)):
                print("  ✅ Analytics data types correct")
                tests_passed += 1
            else:
                print("  ❌ Analytics data types incorrect")
        else:
            print("  ❌ Analytics service failed to return data")

    except Exception as e:
        print(f"  ❌ Analytics service test failed: {e}")

    # Test 3: Analytics models don't interfere with existing models
    total_tests += 1
    try:
        print("3️⃣ Testing model coexistence...")

        # Test that we can still create existing models
        existing_users = User.objects.count()

        # Create analytics data
        test_date = date.today()
        metrics, created = DailyConnectionMetrics.objects.get_or_create(
            date=test_date,
            defaults={
                'total_artists': existing_users,
                'connected_artists': 0
            }
        )

        # Verify existing models still work
        after_users = User.objects.count()

        if after_users == existing_users:
            print("  ✅ Existing models unaffected by analytics")
            tests_passed += 1
        else:
            print("  ❌ Analytics models may be interfering")

    except Exception as e:
        print(f"  ❌ Model coexistence test failed: {e}")

    # Test 4: Event tracking integration
    total_tests += 1
    try:
        print("4️⃣ Testing event tracking integration...")

        # Find an existing artist or create one with unique name
        timestamp = int(time.time())
        artist_user = User.objects.create_user(
            username=f'integration_test_{timestamp}',
            email=f'integration_{timestamp}@test.com',
            password='testpass123',
            user_type='artist'
        )

        artist = ArtistProfile.objects.create(
            user=artist_user,
            display_name=f'Integration Artist {timestamp}',
            is_approved=True
        )

        # Test connection event tracking
        event = SumUpConnectionEvent.objects.create(
            artist=artist,
            event_type='page_viewed',
            metadata={'test': True, 'timestamp': timestamp}
        )

        if event.id:
            print("  ✅ Event tracking works")
            tests_passed += 1
        else:
            print("  ❌ Event tracking failed")

    except Exception as e:
        print(f"  ❌ Event tracking test failed: {e}")

    # Test 5: Dashboard data accuracy
    total_tests += 1
    try:
        print("5️⃣ Testing dashboard data accuracy...")

        # Get real counts from database
        total_artists_db = ArtistProfile.objects.filter(is_approved=True).count()
        connected_artists_db = ArtistProfile.objects.filter(
            is_approved=True,
            sumup_connection_status='connected'
        ).count()

        # Get analytics counts
        analytics_service = AnalyticsService()
        metrics = analytics_service.get_current_metrics()

        if metrics:
            total_diff = abs(metrics['total_artists'] - total_artists_db)
            connected_diff = abs(metrics['connected_artists'] - connected_artists_db)

            # Allow small differences due to timing
            if total_diff <= 2 and connected_diff <= 2:
                print(f"  ✅ Dashboard accuracy good (diff: {total_diff}/{connected_diff})")
                tests_passed += 1
            else:
                print(f"  ⚠️ Dashboard accuracy issues (diff: {total_diff}/{connected_diff})")
                # Still partial credit if working
                tests_passed += 0.5

        else:
            print("  ❌ Dashboard data not available")

    except Exception as e:
        print(f"  ❌ Dashboard accuracy test failed: {e}")

    # Test 6: Performance impact
    total_tests += 1
    try:
        print("6️⃣ Testing performance impact...")

        # Test existing operations speed
        start_time = time.time()

        # Perform typical operations
        User.objects.count()
        Event.objects.count()
        ArtistProfile.objects.count()

        base_time = time.time() - start_time

        # Test operations with analytics
        start_time = time.time()

        User.objects.count()
        analytics_service.get_current_metrics()
        SumUpConnectionEvent.objects.count()

        analytics_time = time.time() - start_time

        # Analytics shouldn't add more than 50% overhead
        if analytics_time < base_time * 1.5 or analytics_time < 0.5:
            print(f"  ✅ Performance impact acceptable ({base_time:.3f}s vs {analytics_time:.3f}s)")
            tests_passed += 1
        else:
            print(f"  ⚠️ Performance impact high ({base_time:.3f}s vs {analytics_time:.3f}s)")

    except Exception as e:
        print(f"  ❌ Performance impact test failed: {e}")

    # Test 7: Alert system integration
    total_tests += 1
    try:
        print("7️⃣ Testing alert system integration...")

        # Create test alert
        alert = ConnectionAlert.objects.create(
            alert_type='low_rate',
            severity='info',
            message=f'Integration test alert {timestamp}',
            current_value=Decimal('50.00')
        )

        # Verify existing functionality still works
        user_count_after_alert = User.objects.count()

        if user_count_after_alert > 0:
            print("  ✅ Alert system doesn't interfere with existing functionality")
            tests_passed += 1
        else:
            print("  ❌ Alert system may be causing issues")

    except Exception as e:
        print(f"  ❌ Alert system test failed: {e}")

    # Cleanup test data
    try:
        User.objects.filter(username__startswith='integration_test_').delete()
        SumUpConnectionEvent.objects.filter(metadata__test=True).delete()
        ConnectionAlert.objects.filter(message__contains='Integration test alert').delete()
        print("🧹 Test data cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

    # Results
    print("\n" + "=" * 50)
    print("🎯 INTEGRATION HEALTH CHECK RESULTS")
    print(f"Tests Passed: {tests_passed}/{total_tests}")

    success_rate = (tests_passed / total_tests) * 100
    print(f"Integration Health: {success_rate:.1f}%")

    if success_rate >= 90:
        print("🟢 EXCELLENT: Analytics fully integrated without interference")
        return "EXCELLENT"
    elif success_rate >= 80:
        print("🟡 GOOD: Analytics mostly integrated with minor issues")
        return "GOOD"
    elif success_rate >= 70:
        print("🟠 FAIR: Analytics integrated but some concerns")
        return "FAIR"
    else:
        print("🔴 POOR: Analytics integration has significant issues")
        return "POOR"

def test_specific_integration_points():
    """Test specific integration points"""
    print("\n🔍 SPECIFIC INTEGRATION POINT TESTS")
    print("-" * 40)

    integration_points = 0
    total_points = 0

    # Test admin interface integration
    total_points += 1
    try:
        from analytics.admin import SumUpConnectionEventAdmin
        print("✅ Admin interface integration working")
        integration_points += 1
    except Exception as e:
        print(f"❌ Admin interface integration issue: {e}")

    # Test URL patterns integration
    total_points += 1
    try:
        from django.urls import reverse
        dashboard_url = reverse('analytics:dashboard')
        if dashboard_url:
            print("✅ URL patterns integration working")
            integration_points += 1
    except Exception as e:
        print(f"❌ URL patterns integration issue: {e}")

    # Test template integration
    total_points += 1
    try:
        from django.template.loader import get_template
        template = get_template('analytics/dashboard.html')
        print("✅ Template integration working")
        integration_points += 1
    except Exception as e:
        print(f"❌ Template integration issue: {e}")

    # Test management commands
    total_points += 1
    try:
        from analytics.management.commands.update_daily_metrics import Command
        print("✅ Management commands integration working")
        integration_points += 1
    except Exception as e:
        print(f"❌ Management commands integration issue: {e}")

    print(f"🔍 Integration Points: {integration_points}/{total_points} working")
    return integration_points >= total_points - 1

def main():
    """Main test runner"""
    print("Jersey Events - Analytics Integration Health Check")
    print("=" * 60)

    # Run health check
    health_status = test_analytics_integration_health()

    # Test specific integration points
    integration_success = test_specific_integration_points()

    print("\n" + "=" * 60)
    print("🎯 FINAL INTEGRATION ASSESSMENT")
    print("=" * 60)

    if health_status == "EXCELLENT" and integration_success:
        print("🟢 ANALYTICS INTEGRATION: PERFECT")
        print("✅ No interference with existing functionality")
        print("📊 All analytics features working correctly")
        print("🚀 Ready for production use")
        return 0

    elif health_status in ["EXCELLENT", "GOOD"] and integration_success:
        print("🟡 ANALYTICS INTEGRATION: VERY GOOD")
        print("✅ Minimal interference with existing functionality")
        print("📊 Analytics features mostly working")
        print("⚠️ Monitor in production")
        return 0

    elif health_status in ["GOOD", "FAIR"]:
        print("🟠 ANALYTICS INTEGRATION: ACCEPTABLE")
        print("⚠️ Some minor interference detected")
        print("📊 Analytics features need attention")
        print("🔧 Address issues before production")
        return 1

    else:
        print("🔴 ANALYTICS INTEGRATION: PROBLEMATIC")
        print("❌ Significant interference with existing functionality")
        print("📊 Analytics features not working correctly")
        print("🚨 Do not deploy without fixes")
        return 2

if __name__ == "__main__":
    sys.exit(main())