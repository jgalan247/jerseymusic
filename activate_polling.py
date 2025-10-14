#!/usr/bin/env python
"""
Activate Payment Polling System
================================
This script activates and verifies the SumUp payment polling system.

Usage:
    python activate_polling.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from django_q.models import Schedule
from django.utils import timezone
from payments.polling_service import polling_service


def check_schedule():
    """Check if polling schedule exists and is configured correctly."""
    print("=" * 80)
    print("STEP 1: Checking Payment Polling Schedule")
    print("=" * 80)

    schedules = Schedule.objects.filter(
        func='payments.polling_service.polling_service.process_pending_payments'
    )

    if schedules.exists():
        schedule = schedules.first()
        print(f"✅ Schedule found!")
        print(f"   Name: {schedule.name or '(unnamed)'}")
        print(f"   Function: {schedule.func}")
        print(f"   Interval: Every {schedule.minutes} minutes")
        print(f"   Repeats: {'Forever' if schedule.repeats == -1 else schedule.repeats}")
        print(f"   Next Run: {schedule.next_run}")

        # Try to get last run time
        try:
            from django_q.models import Task
            last_task = Task.objects.filter(
                name__contains='process_pending_payments'
            ).order_by('-stopped').first()
            if last_task:
                print(f"   Last Run: {last_task.stopped}")
            else:
                print(f"   Last Run: Never")
        except Exception:
            print(f"   Last Run: Unable to determine")

        if schedule.minutes != 5:
            print(f"\n⚠️  WARNING: Schedule interval is {schedule.minutes} minutes, expected 5 minutes")
            response = input("Do you want to fix this? (y/n): ")
            if response.lower() == 'y':
                schedule.minutes = 5
                schedule.save()
                print("✅ Fixed! Schedule now runs every 5 minutes")

        if not schedule.name:
            print("\n💡 TIP: Schedule has no name. Adding descriptive name...")
            schedule.name = 'Payment Polling - Every 5 Minutes'
            schedule.save()
            print("✅ Name added!")

        return True
    else:
        print("❌ No polling schedule found!")
        print("\nCreating schedule now...")

        schedule = Schedule.objects.create(
            name='Payment Polling - Every 5 Minutes',
            func='payments.polling_service.polling_service.process_pending_payments',
            schedule_type='I',  # Interval
            minutes=5,
            repeats=-1  # Forever
        )

        print("✅ Schedule created successfully!")
        print(f"   ID: {schedule.id}")
        print(f"   Next Run: {schedule.next_run}")
        return True


def test_polling_service():
    """Test the polling service manually."""
    print("\n" + "=" * 80)
    print("STEP 2: Testing Polling Service")
    print("=" * 80)

    try:
        print("Running polling service manually...")
        result = polling_service.process_pending_payments()

        print("\n✅ Polling service executed successfully!")

        if result:
            print(f"\nResults:")
            print(f"   Message: {result.get('message', 'N/A')}")
            if 'verified' in result:
                print(f"   Verified: {result['verified']}")
                print(f"   Failed: {result['failed']}")
                print(f"   Still Pending: {result['still_pending']}")
                print(f"   Errors: {result['errors']}")

        return True
    except Exception as e:
        print(f"\n❌ Error testing polling service: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_django_q_cluster():
    """Check if Django-Q cluster is running."""
    print("\n" + "=" * 80)
    print("STEP 3: Checking Django-Q Cluster")
    print("=" * 80)

    # Check if any tasks have been executed recently
    from django_q.models import Task

    recent_tasks = Task.objects.filter(
        started__gte=timezone.now() - timezone.timedelta(minutes=30)
    )

    if recent_tasks.exists():
        print(f"✅ Django-Q cluster appears to be running!")
        print(f"   Recent tasks: {recent_tasks.count()}")

        latest_task = recent_tasks.order_by('-stopped').first()
        if latest_task:
            print(f"   Latest task: {latest_task.name}")
            print(f"   Completed: {latest_task.stopped}")
            print(f"   Success: {latest_task.success}")
    else:
        print("⚠️  No recent tasks found - Django-Q cluster may not be running")
        print("\nTo start Django-Q cluster:")
        print("   Development: python manage.py qcluster")
        print("   Production:  sudo systemctl start django-q")

    return True


def show_next_steps():
    """Show next steps for activation."""
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)

    print("\n📋 Development Environment:")
    print("   1. Open a new terminal")
    print("   2. Navigate to project: cd /Users/josegalan/Documents/jersey_music")
    print("   3. Activate virtualenv: source venv/bin/activate")
    print("   4. Start Django-Q cluster: python manage.py qcluster")
    print("   5. Keep it running!")

    print("\n📋 Production Environment:")
    print("   1. Configure supervisor: See supervisor_django_q.conf")
    print("   2. Start service: sudo supervisorctl start django_q")
    print("   3. Enable auto-start: sudo supervisorctl enable django_q")
    print("   4. Check status: sudo supervisorctl status django_q")

    print("\n📋 Testing:")
    print("   1. Create a test order")
    print("   2. Complete SumUp payment")
    print("   3. Wait 5 minutes")
    print("   4. Check email for tickets")
    print("   5. Verify order status in admin: /admin/orders/order/")

    print("\n📋 Monitoring:")
    print("   - View schedules: /admin/django_q/schedule/")
    print("   - View tasks: /admin/django_q/task/")
    print("   - Manual test: python manage.py run_payment_polling --verbose")
    print("   - Check logs: tail -f logs/payment_polling.log")


def main():
    """Main activation script."""
    print("\n" + "=" * 80)
    print("🚀 PAYMENT POLLING SYSTEM - ACTIVATION SCRIPT")
    print("=" * 80)
    print("\nThis script will:")
    print("  1. Check if polling schedule is configured")
    print("  2. Test the polling service manually")
    print("  3. Check Django-Q cluster status")
    print("  4. Show next steps")

    input("\nPress Enter to continue...")

    # Step 1: Check schedule
    if not check_schedule():
        print("\n❌ Failed to configure schedule. Exiting.")
        sys.exit(1)

    # Step 2: Test polling service
    if not test_polling_service():
        print("\n⚠️  Warning: Polling service test failed, but continuing...")

    # Step 3: Check Django-Q cluster
    check_django_q_cluster()

    # Step 4: Show next steps
    show_next_steps()

    print("\n" + "=" * 80)
    print("✅ ACTIVATION SCRIPT COMPLETE!")
    print("=" * 80)
    print("\n💡 IMPORTANT: Make sure Django-Q cluster is running!")
    print("   Run: python manage.py qcluster")


if __name__ == '__main__':
    main()
