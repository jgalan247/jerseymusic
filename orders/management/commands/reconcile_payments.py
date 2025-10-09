"""
Payment Reconciliation Management Command

This command performs daily reconciliation between Jersey Events orders
and SumUp payment dashboard to detect payment discrepancies.

Usage:
    python manage.py reconcile_payments [--days=N] [--fix-discrepancies]

SECURITY NOTE: This helps detect potential payment fraud or verification failures.
"""
import logging
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.mail import mail_admins
from django.conf import settings
from orders.models import Order
from payments.models import SumUpCheckout

logger = logging.getLogger('payment_audit')


class Command(BaseCommand):
    help = 'Reconcile Jersey Events orders with SumUp payments for fraud detection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to reconcile (default: 1 day)'
        )
        parser.add_argument(
            '--fix-discrepancies',
            action='store_true',
            help='Automatically fix obvious discrepancies (use with caution)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        days = options['days']
        fix_discrepancies = options['fix_discrepancies']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))

        self.stdout.write(f'🔍 Starting payment reconciliation for last {days} day(s)...')

        start_date = timezone.now() - timedelta(days=days)

        try:
            # Get orders from the specified period
            orders = self.get_orders_for_reconciliation(start_date)

            # Get SumUp transactions for the same period
            sumup_transactions = self.get_sumup_transactions(start_date)

            # Perform reconciliation
            discrepancies = self.reconcile_orders_with_sumup(orders, sumup_transactions)

            # Report findings
            self.report_reconciliation_results(orders, sumup_transactions, discrepancies)

            # Fix discrepancies if requested
            if fix_discrepancies and not dry_run:
                self.fix_payment_discrepancies(discrepancies)

            # Send admin alert if discrepancies found
            if discrepancies:
                self.send_admin_alert(discrepancies, days)

        except Exception as e:
            logger.error(f"Payment reconciliation failed: {e}")
            raise CommandError(f'Reconciliation failed: {e}')

    def get_orders_for_reconciliation(self, start_date):
        """Get orders that should have payments in the specified period."""
        orders = Order.objects.filter(
            created_at__gte=start_date,
            status__in=['confirmed', 'pending_verification', 'processing']
        ).order_by('-created_at')

        self.stdout.write(f'📋 Found {orders.count()} orders to reconcile')
        return orders

    def get_sumup_transactions(self, start_date):
        """
        Get SumUp transactions for the period.

        NOTE: This is a simplified implementation. In production, you would:
        1. Use SumUp's API to fetch transactions
        2. Handle pagination for large datasets
        3. Cache results to avoid rate limiting
        """
        self.stdout.write('💳 Fetching SumUp transactions...')

        try:
            from payments.sumup import get_access_token

            access_token = get_access_token()
            if not access_token:
                raise Exception("Failed to get SumUp access token")

            # Format date for SumUp API (ISO 8601)
            start_date_str = start_date.isoformat()

            # NOTE: SumUp API endpoint for transactions
            # This may need adjustment based on actual SumUp API documentation
            url = "https://api.sumup.com/v0.1/me/transactions"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            params = {
                'start_date': start_date_str,
                'limit': 100  # Adjust based on your volume
            }

            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                transactions = response.json()
                self.stdout.write(f'💳 Retrieved {len(transactions)} SumUp transactions')
                return transactions
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  SumUp API returned {response.status_code}. '
                        f'Manual verification may be needed.'
                    )
                )
                return []

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Could not fetch SumUp transactions: {e}. '
                    f'Proceeding with order-only analysis.'
                )
            )
            return []

    def reconcile_orders_with_sumup(self, orders, sumup_transactions):
        """Compare orders against SumUp transactions to find discrepancies."""
        discrepancies = []

        self.stdout.write('🔍 Analyzing payment discrepancies...')

        for order in orders:
            order_issues = self.check_order_payment_status(order, sumup_transactions)
            if order_issues:
                discrepancies.extend(order_issues)

        return discrepancies

    def check_order_payment_status(self, order, sumup_transactions):
        """Check if an individual order has payment issues."""
        issues = []

        # Check 1: Confirmed orders should be paid
        if order.status == 'confirmed' and not order.is_paid:
            issues.append({
                'type': 'confirmed_but_not_paid',
                'order': order,
                'severity': 'HIGH',
                'description': f'Order {order.order_number} is confirmed but not marked as paid'
            })

        # Check 2: Paid orders should have payment timestamp
        if order.is_paid and not order.paid_at:
            issues.append({
                'type': 'paid_without_timestamp',
                'order': order,
                'severity': 'MEDIUM',
                'description': f'Order {order.order_number} is paid but has no payment timestamp'
            })

        # Check 3: Pending verification orders (critical security check)
        if order.status == 'pending_verification':
            # Check if this order has been pending too long
            hours_pending = (timezone.now() - order.created_at).total_seconds() / 3600
            if hours_pending > 24:
                issues.append({
                    'type': 'long_pending_verification',
                    'order': order,
                    'severity': 'CRITICAL',
                    'description': f'Order {order.order_number} pending verification for {hours_pending:.1f} hours'
                })

        # Check 4: Try to find matching SumUp transaction
        if sumup_transactions:
            matching_transaction = self.find_matching_sumup_transaction(order, sumup_transactions)
            if order.status == 'confirmed' and not matching_transaction:
                issues.append({
                    'type': 'no_sumup_match',
                    'order': order,
                    'severity': 'HIGH',
                    'description': f'Order {order.order_number} confirmed but no matching SumUp transaction found'
                })

        return issues

    def find_matching_sumup_transaction(self, order, sumup_transactions):
        """Try to find a SumUp transaction that matches this order."""
        # This is simplified - in production you'd have more sophisticated matching
        for transaction in sumup_transactions:
            # Match by amount and approximate timestamp
            if (abs(float(transaction.get('amount', 0)) - float(order.total)) < 0.01 and
                self.timestamps_close(order.created_at, transaction.get('timestamp'))):
                return transaction
        return None

    def timestamps_close(self, order_time, transaction_time, tolerance_minutes=30):
        """Check if two timestamps are within tolerance."""
        if not transaction_time:
            return False

        try:
            # Parse SumUp timestamp (format may vary)
            if isinstance(transaction_time, str):
                tx_time = datetime.fromisoformat(transaction_time.replace('Z', '+00:00'))
            else:
                tx_time = transaction_time

            diff = abs((order_time - tx_time).total_seconds() / 60)
            return diff <= tolerance_minutes

        except Exception:
            return False

    def report_reconciliation_results(self, orders, sumup_transactions, discrepancies):
        """Generate reconciliation report."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('📊 PAYMENT RECONCILIATION REPORT')
        self.stdout.write('='*60)

        total_orders = orders.count()
        confirmed_orders = orders.filter(status='confirmed').count()
        pending_verification = orders.filter(status='pending_verification').count()
        total_amount = sum(order.total for order in orders)

        self.stdout.write(f'📋 Total Orders: {total_orders}')
        self.stdout.write(f'✅ Confirmed Orders: {confirmed_orders}')
        self.stdout.write(f'⏳ Pending Verification: {pending_verification}')
        self.stdout.write(f'💰 Total Amount: £{total_amount}')
        self.stdout.write(f'💳 SumUp Transactions: {len(sumup_transactions)}')

        if discrepancies:
            self.stdout.write(f'\n🚨 DISCREPANCIES FOUND: {len(discrepancies)}')

            for discrepancy in discrepancies:
                severity_color = {
                    'CRITICAL': self.style.ERROR,
                    'HIGH': self.style.WARNING,
                    'MEDIUM': self.style.HTTP_INFO
                }.get(discrepancy['severity'], self.style.NOTICE)

                self.stdout.write(
                    severity_color(
                        f"  {discrepancy['severity']}: {discrepancy['description']}"
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ No discrepancies found!'))

    def fix_payment_discrepancies(self, discrepancies):
        """Automatically fix obvious discrepancies (use with extreme caution)."""
        self.stdout.write('\n🔧 Attempting to fix discrepancies...')

        fixed_count = 0

        for discrepancy in discrepancies:
            if discrepancy['type'] == 'paid_without_timestamp':
                # Safe fix: add payment timestamp
                order = discrepancy['order']
                order.paid_at = order.updated_at or order.created_at
                order.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅ Fixed: Added payment timestamp to {order.order_number}"
                    )
                )
                fixed_count += 1

            elif discrepancy['type'] == 'long_pending_verification':
                # This requires manual review - log for admin attention
                order = discrepancy['order']
                logger.error(
                    f"URGENT: Order {order.order_number} needs immediate manual verification"
                )

        self.stdout.write(f'\n🔧 Fixed {fixed_count} discrepancies automatically')
        self.stdout.write(
            self.style.WARNING(
                '⚠️  Remaining discrepancies require manual review'
            )
        )

    def send_admin_alert(self, discrepancies, days):
        """Send email alert to admins about payment discrepancies."""
        critical_count = sum(1 for d in discrepancies if d['severity'] == 'CRITICAL')
        high_count = sum(1 for d in discrepancies if d['severity'] == 'HIGH')

        subject = f"🚨 Payment Discrepancies Found - {critical_count} Critical, {high_count} High"

        message = f"""
URGENT: Payment reconciliation found discrepancies that require immediate attention.

SUMMARY:
- Period: Last {days} day(s)
- Total Discrepancies: {len(discrepancies)}
- Critical Issues: {critical_count}
- High Priority Issues: {high_count}

CRITICAL ISSUES REQUIRING IMMEDIATE ACTION:
"""

        for discrepancy in discrepancies:
            if discrepancy['severity'] == 'CRITICAL':
                message += f"\n• {discrepancy['description']}"
                message += f"\n  Order: {discrepancy['order'].order_number}"
                message += f"\n  Customer: {discrepancy['order'].email}"
                message += f"\n  Amount: £{discrepancy['order'].total}"

        message += f"""

ACTION REQUIRED:
1. Review Django admin: /admin/orders/order/
2. Check SumUp dashboard for payment verification
3. Contact customers if payments are invalid
4. Run: python manage.py reconcile_payments --fix-discrepancies

This requires immediate attention to maintain payment security.
        """

        try:
            mail_admins(
                subject=subject,
                message=message,
                fail_silently=False
            )
            self.stdout.write(
                self.style.SUCCESS('📧 Admin alert sent successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to send admin alert: {e}')
            )
            # Log to console as fallback
            print(f'\n🚨 URGENT: {subject}')
            print(message)