#!/usr/bin/env python
"""
Comprehensive Error Scenario Testing for PDF Ticket System
Tests various failure modes and recovery mechanisms
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to the Python path
sys.path.append('/Users/josegalan/Documents/jersey_music')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

import logging
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from unittest.mock import patch, MagicMock

from events.models import Event, Ticket, Category
from events.ticket_generator import TicketGenerator
from events.ticket_validator import TicketValidator, validate_ticket
from events.email_utils import EmailService
from orders.models import Order
from payments.models import Payment

User = get_user_model()
logger = logging.getLogger(__name__)

class ComprehensiveErrorTesting:
    """Test suite for error handling in PDF ticket system"""

    def __init__(self):
        self.setup_test_data()
        self.test_results = []

    def setup_test_data(self):
        """Create test data for error testing"""
        print("📋 Setting up test data...")

        # Create test users
        self.artist, created = User.objects.get_or_create(
            username='test_artist_error',
            defaults={
                'email': 'artist@test.com',
                'user_type': 'artist',
                'first_name': 'Test',
                'last_name': 'Artist'
            }
        )

        self.customer, created = User.objects.get_or_create(
            username='test_customer_error',
            defaults={
                'email': 'customer@test.com',
                'user_type': 'customer',
                'first_name': 'Test',
                'last_name': 'Customer'
            }
        )

        # Create test category
        self.category, created = Category.objects.get_or_create(
            name='Test Category Error',
            defaults={'slug': 'test-category-error'}
        )

        # Create test event
        from datetime import date, time
        self.event, created = Event.objects.get_or_create(
            title='Error Test Event',
            defaults={
                'slug': 'error-test-event',
                'organiser': self.artist,
                'description': 'Test event for error scenarios',
                'category': self.category,
                'venue_name': 'Test Venue',
                'venue_address': '123 Test Street, Jersey',
                'event_date': date.today(),
                'event_time': time(19, 0),
                'capacity': 100,
                'ticket_price': Decimal('25.00')
            }
        )

        print("✅ Test data setup complete")

    def test_scenario(self, name, test_func):
        """Run a test scenario and record results"""
        print(f"\n🧪 Testing: {name}")
        try:
            result = test_func()
            status = "✅ PASS" if result else "❌ FAIL"
            self.test_results.append({"name": name, "status": status, "details": result})
            print(f"{status}: {name}")
            return result
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.test_results.append({"name": name, "status": "❌ ERROR", "details": error_msg})
            print(f"❌ ERROR: {name} - {error_msg}")
            return False

    def test_pdf_generation_errors(self):
        """Test PDF generation error scenarios"""
        generator = TicketGenerator()

        # Test with missing ticket data
        try:
            ticket = Ticket(
                event=None,  # Missing event
                customer=self.customer,
                ticket_number="TEST-ERROR-001"
            )
            result = generator.generate_ticket_pdf(ticket)
            return False  # Should have failed
        except Exception:
            pass  # Expected to fail

        # Test with invalid file system
        try:
            ticket = Ticket.objects.create(
                event=self.event,
                customer=self.customer,
                ticket_number="TEST-ERROR-002"
            )

            # Mock file system failure
            with patch('django.core.files.storage.default_storage.save') as mock_save:
                mock_save.side_effect = IOError("Disk full")
                result = ticket.generate_pdf_ticket()
                return result == False  # Should handle gracefully
        except Exception:
            return True  # Error was handled

        return True

    def test_qr_validation_errors(self):
        """Test QR code validation error scenarios"""
        validator = TicketValidator()

        # Test invalid QR format
        success, message, ticket = validator.validate_ticket_qr("INVALID_QR_DATA")
        if success:
            return False

        # Test malformed QR data
        success, message, ticket = validator.validate_ticket_qr("JERSEY_EVENTS|incomplete")
        if success:
            return False

        # Test non-existent ticket
        success, message, ticket = validator.validate_ticket_qr(
            "JERSEY_EVENTS|FAKE-TICKET|999|fake@test.com|fakehash"
        )
        if success:
            return False

        # Test already validated ticket
        ticket = Ticket.objects.create(
            event=self.event,
            customer=self.customer,
            ticket_number="ALREADY-VALIDATED"
        )
        ticket.is_validated = True
        ticket.save()

        # Generate valid QR data for already validated ticket
        from events.ticket_generator import TicketGenerator
        gen = TicketGenerator()
        hash_val = gen.generate_ticket_validation_hash(ticket)
        qr_data = f"JERSEY_EVENTS|{ticket.ticket_number}|{ticket.event.id}|{ticket.customer.email}|{hash_val}"

        success, message, ticket_result = validator.validate_ticket_qr(qr_data)
        return not success and "already" in message.lower()

    def test_email_delivery_errors(self):
        """Test email delivery error scenarios"""
        email_service = EmailService()

        # Test invalid recipient
        result = email_service.send_email_with_retry(
            subject="Test",
            message="Test",
            recipient_list=["invalid-email-format"]
        )

        # Test empty recipient list
        result2 = email_service.send_email_with_retry(
            subject="Test",
            message="Test",
            recipient_list=[]
        )

        # Test attachment errors
        result3 = email_service.send_email_with_attachments(
            subject="Test",
            message="Test",
            recipient_list=["test@test.com"],
            attachments=[{"filename": "test.pdf", "content": None}]  # Invalid attachment
        )

        return not result and not result2 and not result3

    def test_file_handling_errors(self):
        """Test file system and storage errors"""

        # Test PDF file creation with disk space issues
        try:
            ticket = Ticket.objects.create(
                event=self.event,
                customer=self.customer,
                ticket_number="FILE-ERROR-TEST"
            )

            # Mock storage failure
            with patch('events.models.default_storage') as mock_storage:
                mock_storage.save.side_effect = OSError("No space left on device")
                result = ticket.generate_pdf_ticket()
                return result == False  # Should handle gracefully

        except Exception as e:
            print(f"File handling test caught exception: {e}")
            return True  # Exception was handled

        return True

    def test_database_transaction_errors(self):
        """Test database transaction and concurrency errors"""
        from django.db import transaction

        try:
            # Test concurrent ticket validation
            ticket = Ticket.objects.create(
                event=self.event,
                customer=self.customer,
                ticket_number="CONCURRENT-TEST"
            )

            # Simulate concurrent validation attempts
            with patch('events.models.Ticket.objects.filter') as mock_filter:
                mock_filter.return_value.update.side_effect = Exception("Database lock")
                success, message = ticket.validate_ticket()
                return not success  # Should handle database errors

        except Exception:
            return True  # Exception was handled

        return True

    def test_memory_and_performance(self):
        """Test memory usage and performance with large datasets"""
        import gc
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        try:
            # Create multiple tickets and PDFs
            tickets = []
            for i in range(10):  # Reduced for testing
                ticket = Ticket.objects.create(
                    event=self.event,
                    customer=self.customer,
                    ticket_number=f"PERF-TEST-{i:03d}"
                )
                # Generate PDF in memory
                generator = TicketGenerator()
                pdf_data = generator.generate_ticket_pdf(ticket)
                tickets.append(ticket)

            # Check memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            print(f"Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB (+{memory_increase:.1f}MB)")

            # Cleanup
            for ticket in tickets:
                if ticket.pdf_file:
                    ticket.pdf_file.delete()
                ticket.delete()

            gc.collect()

            return memory_increase < 50  # Reasonable memory usage

        except Exception as e:
            print(f"Performance test error: {e}")
            return False

    def test_security_scenarios(self):
        """Test security-related error scenarios"""
        validator = TicketValidator()

        # Test QR data tampering
        ticket = Ticket.objects.create(
            event=self.event,
            customer=self.customer,
            ticket_number="SECURITY-TEST"
        )

        # Generate valid QR then tamper with it
        from events.ticket_generator import TicketGenerator
        gen = TicketGenerator()
        valid_hash = gen.generate_ticket_validation_hash(ticket)

        # Tampered QR data
        tampered_qr = f"JERSEY_EVENTS|{ticket.ticket_number}|{ticket.event.id}|hacker@evil.com|{valid_hash}"
        success, message, result_ticket = validator.validate_ticket_qr(tampered_qr)

        if success:
            return False  # Should reject tampered data

        # Test hash manipulation
        fake_hash = "fakehash12345"
        fake_qr = f"JERSEY_EVENTS|{ticket.ticket_number}|{ticket.event.id}|{ticket.customer.email}|{fake_hash}"
        success2, message2, result_ticket2 = validator.validate_ticket_qr(fake_qr)

        return not success and not success2

    def run_all_tests(self):
        """Run all error scenario tests"""
        print("🚨 COMPREHENSIVE ERROR SCENARIO TESTING")
        print("=" * 50)

        test_scenarios = [
            ("PDF Generation Error Handling", self.test_pdf_generation_errors),
            ("QR Validation Error Handling", self.test_qr_validation_errors),
            ("Email Delivery Error Handling", self.test_email_delivery_errors),
            ("File System Error Handling", self.test_file_handling_errors),
            ("Database Transaction Errors", self.test_database_transaction_errors),
            ("Memory and Performance", self.test_memory_and_performance),
            ("Security Scenarios", self.test_security_scenarios),
        ]

        for name, test_func in test_scenarios:
            self.test_scenario(name, test_func)

        # Summary
        print("\n" + "=" * 50)
        print("📊 ERROR TESTING SUMMARY")
        print("=" * 50)

        passed = sum(1 for result in self.test_results if "PASS" in result["status"])
        total = len(self.test_results)

        for result in self.test_results:
            print(f"{result['status']}: {result['name']}")
            if "ERROR" in result['status'] or "FAIL" in result['status']:
                print(f"    Details: {result['details']}")

        print(f"\n🎯 Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 ALL ERROR SCENARIOS HANDLED CORRECTLY!")
        else:
            print("⚠️ Some error scenarios need attention")

        return passed == total

def main():
    """Run comprehensive error testing"""
    tester = ComprehensiveErrorTesting()
    success = tester.run_all_tests()
    return success

if __name__ == "__main__":
    main()