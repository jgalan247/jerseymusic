#!/usr/bin/env python
"""
Test Payment Polling System
============================
This script tests the payment polling system end-to-end.

Usage:
    python test_payment_polling.py
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from orders.models import Order
from payments.models import SumUpCheckout
from payments.polling_service import polling_service


def test_polling_service_dry_run():
    """Test the polling service without actual orders."""
    print("=" * 80)
    print("TEST 1: Polling Service Dry Run")
    print("=" * 80)

    try:
        result = polling_service.process_pending_payments()

        print("✅ Polling service executed successfully!")
        print(f"\nResult: {result}")

        if result.get('message'):
            print(f"Message: {result['message']}")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_pending_orders():
    """Check for pending orders in the system."""
    print("\n" + "=" * 80)
    print("TEST 2: Check Pending Orders")
    print("=" * 80)

    # Find pending orders
    pending_orders = Order.objects.filter(
        status='pending_verification',
        created_at__gte=timezone.now() - timedelta(hours=2)
    )

    print(f"Found {pending_orders.count()} pending orders")

    if pending_orders.exists():
        print("\nPending Orders:")
        for order in pending_orders[:10]:  # Show first 10
            print(f"\n  Order: {order.order_number}")
            print(f"  Status: {order.status}")
            print(f"  Total: £{order.total}")
            print(f"  Email: {order.email}")
            print(f"  Created: {order.created_at}")
            print(f"  Age: {timezone.now() - order.created_at}")

            # Check if checkout exists
            try:
                checkout = SumUpCheckout.objects.get(order=order)
                print(f"  Checkout ID: {checkout.sumup_checkout_id}")
                print(f"  Checkout Status: {checkout.status}")
            except SumUpCheckout.DoesNotExist:
                print(f"  ⚠️  WARNING: No checkout record found!")

        if pending_orders.count() > 10:
            print(f"\n  ... and {pending_orders.count() - 10} more")

    else:
        print("\n✅ No pending orders - system is clean!")

    return True


def check_completed_orders():
    """Check recently completed orders."""
    print("\n" + "=" * 80)
    print("TEST 3: Check Recently Completed Orders")
    print("=" * 80)

    # Find completed orders from last 24 hours
    completed_orders = Order.objects.filter(
        status='completed',
        paid_at__gte=timezone.now() - timedelta(hours=24)
    )

    print(f"Found {completed_orders.count()} completed orders (last 24 hours)")

    if completed_orders.exists():
        print("\nRecent Completions:")
        for order in completed_orders[:5]:  # Show first 5
            print(f"\n  Order: {order.order_number}")
            print(f"  Total: £{order.total}")
            print(f"  Email: {order.email}")
            print(f"  Paid At: {order.paid_at}")
            print(f"  Transaction ID: {order.transaction_id or 'N/A'}")

            # Check tickets
            ticket_count = order.tickets.count()
            print(f"  Tickets Generated: {ticket_count}")

        if completed_orders.count() > 5:
            print(f"\n  ... and {completed_orders.count() - 5} more")

    else:
        print("\n⚠️  No completed orders in last 24 hours")

    return True


def check_failed_expired_orders():
    """Check failed and expired orders."""
    print("\n" + "=" * 80)
    print("TEST 4: Check Failed/Expired Orders")
    print("=" * 80)

    # Failed orders
    failed_orders = Order.objects.filter(
        status='failed',
        created_at__gte=timezone.now() - timedelta(days=7)
    )

    print(f"Failed orders (last 7 days): {failed_orders.count()}")

    if failed_orders.exists():
        for order in failed_orders[:3]:
            print(f"  - {order.order_number}: £{order.total} ({order.created_at})")

    # Expired orders
    expired_orders = Order.objects.filter(
        status='expired',
        created_at__gte=timezone.now() - timedelta(days=7)
    )

    print(f"Expired orders (last 7 days): {expired_orders.count()}")

    if expired_orders.exists():
        for order in expired_orders[:3]:
            print(f"  - {order.order_number}: £{order.total} ({order.created_at})")

    # Manual review needed
    review_orders = Order.objects.filter(
        status='requires_manual_review',
        created_at__gte=timezone.now() - timedelta(days=30)
    )

    print(f"Requires manual review (last 30 days): {review_orders.count()}")

    if review_orders.exists():
        print("\n⚠️  WARNING: Orders requiring manual review:")
        for order in review_orders:
            print(f"\n  Order: {order.order_number}")
            print(f"  Total: £{order.total}")
            print(f"  Email: {order.email}")
            print(f"  Notes: {order.payment_notes}")

    return True


def check_django_q_tasks():
    """Check Django-Q task history."""
    print("\n" + "=" * 80)
    print("TEST 5: Django-Q Task History")
    print("=" * 80)

    from django_q.models import Task, Schedule

    # Check schedule
    schedules = Schedule.objects.filter(
        func='payments.polling_service.polling_service.process_pending_payments'
    )

    if schedules.exists():
        schedule = schedules.first()
        print(f"✅ Polling schedule exists")
        print(f"   Name: {schedule.name or '(unnamed)'}")
        print(f"   Interval: Every {schedule.minutes} minutes")
        print(f"   Next Run: {schedule.next_run}")
    else:
        print("❌ No polling schedule found!")

    # Check recent tasks
    recent_tasks = Task.objects.filter(
        started__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-stopped')[:10]

    print(f"\nRecent tasks (last 24 hours): {recent_tasks.count()}")

    if recent_tasks.exists():
        print("\nLast 10 tasks:")
        for task in recent_tasks:
            status = "✅" if task.success else "❌"
            print(f"  {status} {task.name}")
            print(f"     Started: {task.started}")
            print(f"     Duration: {(task.stopped - task.started).total_seconds():.2f}s")
            if not task.success and task.result:
                print(f"     Error: {task.result[:100]}")
    else:
        print("\n⚠️  No recent tasks - Django-Q cluster may not be running!")
        print("   Run: python manage.py qcluster")

    return True


def show_monitoring_commands():
    """Show useful monitoring commands."""
    print("\n" + "=" * 80)
    print("MONITORING COMMANDS")
    print("=" * 80)

    print("\n📊 Check System Status:")
    print("   python test_payment_polling.py")

    print("\n🔄 Manual Polling Test:")
    print("   python manage.py run_payment_polling --verbose")

    print("\n📋 View Django-Q Admin:")
    print("   Schedules: http://localhost:8000/admin/django_q/schedule/")
    print("   Tasks:     http://localhost:8000/admin/django_q/task/")

    print("\n📝 Check Logs:")
    print("   tail -f logs/django_q.log")
    print("   tail -f logs/payment_polling.log")

    print("\n🐛 Django Shell Commands:")
    print("   python manage.py shell")
    print("   >>> from orders.models import Order")
    print("   >>> Order.objects.filter(status='pending_verification').count()")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("🧪 PAYMENT POLLING SYSTEM - TEST SUITE")
    print("=" * 80)

    print("\nThis script will:")
    print("  1. Test polling service execution")
    print("  2. Check pending orders")
    print("  3. Check completed orders")
    print("  4. Check failed/expired orders")
    print("  5. Check Django-Q task history")

    input("\nPress Enter to continue...")

    # Run tests
    tests = [
        ("Polling Service Dry Run", test_polling_service_dry_run),
        ("Check Pending Orders", check_pending_orders),
        ("Check Completed Orders", check_completed_orders),
        ("Check Failed/Expired Orders", check_failed_expired_orders),
        ("Check Django-Q Tasks", check_django_q_tasks),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Show summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed")

    # Show monitoring commands
    show_monitoring_commands()

    print("\n" + "=" * 80)
    print("✅ TEST SUITE COMPLETE!")
    print("=" * 80)


if __name__ == '__main__':
    main()
