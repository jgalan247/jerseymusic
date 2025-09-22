#!/usr/bin/env python
"""
Diagnostic script to identify and fix test collection errors in Jersey Artwork project.
Run this from your project root: python diagnose_tests.py
"""

import os
import sys
import importlib.util
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'artworks.settings_test'

# Initialize Django
import django
django.setup()

def check_import(module_path, test_name):
    """Check if a module can be imported and identify issues."""
    print(f"\n{'='*60}")
    print(f"Checking: {test_name}")
    print(f"Path: {module_path}")
    print('-'*60)
    
    try:
        # Check if file exists
        if not os.path.exists(module_path):
            print(f"❌ File does not exist: {module_path}")
            return False
            
        # Try to load the module
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        if spec is None:
            print(f"❌ Could not load spec for {module_path}")
            return False
            
        module = importlib.util.module_from_spec(spec)
        
        # Try to execute the module
        spec.loader.exec_module(module)
        print(f"✅ Module loaded successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        
        # Provide specific fixes for common import errors
        error_str = str(e).lower()
        if 'no module named' in error_str:
            missing_module = str(e).split("'")[1]
            print(f"\n💡 Fix: Install or create missing module '{missing_module}'")
            
            # Common fixes
            if missing_module in ['factory', 'factory_boy']:
                print("   Run: pip install factory-boy")
            elif missing_module == 'selenium':
                print("   Run: pip install selenium")
            elif missing_module == 'pytest':
                print("   Run: pip install pytest pytest-django")
            elif 'forms' in missing_module:
                print(f"   Create the forms module: touch {missing_module.replace('.', '/')}.py")
                
    except SyntaxError as e:
        print(f"❌ Syntax Error: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
        
    return False

def check_django_apps():
    """Check if all required Django apps are installed."""
    print("\n" + "="*60)
    print("Checking Django Apps Configuration")
    print("-"*60)
    
    from django.conf import settings
    required_apps = ['accounts', 'orders', 'cart', 'artworks']
    
    for app in required_apps:
        if app in settings.INSTALLED_APPS:
            print(f"✅ {app} is installed")
        else:
            print(f"❌ {app} is NOT in INSTALLED_APPS")
            print(f"   Add '{app}' to INSTALLED_APPS in settings_test.py")

def check_test_dependencies():
    """Check if all test dependencies are installed."""
    print("\n" + "="*60)
    print("Checking Test Dependencies")
    print("-"*60)
    
    dependencies = {
        'pytest': 'pytest',
        'pytest_django': 'pytest-django',
        'factory': 'factory-boy',
        'selenium': 'selenium',
    }
    
    for module_name, package_name in dependencies.items():
        try:
            __import__(module_name)
            print(f"✅ {package_name} is installed")
        except ImportError:
            print(f"❌ {package_name} is NOT installed")
            print(f"   Run: pip install {package_name}")

def suggest_fixes_for_common_issues():
    """Provide fixes for common test collection issues."""
    print("\n" + "="*60)
    print("Common Fixes for Test Collection Errors")
    print("="*60)
    
    fixes = """
1. Missing Forms Module:
   If you haven't created forms.py files yet:
   ```bash
   touch accounts/forms.py
   touch orders/forms.py
   touch cart/forms.py
   ```

2. Missing Test Files:
   Ensure test directory structure exists:
   ```bash
   mkdir -p accounts/tests/test_models
   mkdir -p accounts/tests/test_forms
   mkdir -p accounts/tests/test_views
   mkdir -p orders/tests/test_models
   mkdir -p orders/tests/test_forms
   mkdir -p orders/tests/test_views
   mkdir -p cart/tests/test_models
   mkdir -p tests/integration
   mkdir -p tests/e2e
   
   # Create __init__.py files
   touch accounts/tests/__init__.py
   touch orders/tests/__init__.py
   touch cart/tests/__init__.py
   touch tests/__init__.py
   ```

3. Create Basic Forms (if missing):
   ```python
   # accounts/forms.py
   from django import forms
   from django.contrib.auth.forms import UserCreationForm
   from django.contrib.auth import get_user_model
   
   User = get_user_model()
   
   class CustomerRegistrationForm(UserCreationForm):
       phone_number = forms.CharField(max_length=20, required=False)
       address_line_1 = forms.CharField(max_length=255)
       address_line_2 = forms.CharField(max_length=255, required=False)
       parish = forms.ChoiceField(choices=[
           ('St. Helier', 'St. Helier'),
           ('St. Brelade', 'St. Brelade'),
           ('St. Clement', 'St. Clement'),
           ('St. John', 'St. John'),
           ('St. Lawrence', 'St. Lawrence'),
           ('St. Martin', 'St. Martin'),
           ('St. Mary', 'St. Mary'),
           ('St. Ouen', 'St. Ouen'),
           ('St. Peter', 'St. Peter'),
           ('St. Saviour', 'St. Saviour'),
           ('Grouville', 'Grouville'),
           ('Trinity', 'Trinity'),
       ])
       postcode = forms.RegexField(
           regex=r'^JE[1-5]\s?\d[A-Z]{2}$',
           error_message='Enter a valid Jersey postcode (e.g., JE2 3AB)'
       )
       
       class Meta:
           model = User
           fields = ('username', 'email', 'password1', 'password2',
                    'first_name', 'last_name')
   
   class ArtistRegistrationForm(CustomerRegistrationForm):
       bio = forms.CharField(widget=forms.Textarea, required=False)
       artist_name = forms.CharField(max_length=100)
       portfolio_website = forms.URLField(required=False)
   
   class UserUpdateForm(forms.ModelForm):
       class Meta:
           model = User
           fields = ['first_name', 'last_name', 'email']
   
   class CustomerProfileUpdateForm(forms.Form):
       phone_number = forms.CharField(max_length=20, required=False)
       address_line_1 = forms.CharField(max_length=255)
       parish = forms.ChoiceField(choices=[...])  # Same as above
       postcode = forms.CharField(max_length=10)
   
   class ArtistProfileUpdateForm(forms.Form):
       bio = forms.CharField(widget=forms.Textarea, required=False)
       artist_name = forms.CharField(max_length=100)
       portfolio_website = forms.URLField(required=False)
   ```

   ```python
   # orders/forms.py
   from django import forms
   from .models import Order
   
   class CheckoutForm(forms.Form):
       first_name = forms.CharField(max_length=50)
       last_name = forms.CharField(max_length=50)
       email = forms.EmailField()
       phone_number = forms.CharField(max_length=20)
       address_line_1 = forms.CharField(max_length=255)
       address_line_2 = forms.CharField(max_length=255, required=False)
       parish = forms.ChoiceField(choices=[
           ('St. Helier', 'St. Helier'),
           # ... add all parishes
       ])
       postcode = forms.RegexField(
           regex=r'^JE[1-5]\s?\d[A-Z]{2}$',
           error_message='Enter a valid Jersey postcode'
       )
       delivery_instructions = forms.CharField(
           widget=forms.Textarea,
           required=False
       )
   
   class RefundRequestForm(forms.Form):
       reason = forms.ChoiceField(choices=[
           ('damaged', 'Damaged'),
           ('not_as_described', 'Not as described'),
           ('never_received', 'Never received'),
           ('quality_issue', 'Quality issue'),
           ('other', 'Other'),
       ])
       description = forms.CharField(widget=forms.Textarea)
       requested_amount = forms.DecimalField(max_digits=10, decimal_places=2)
   ```

4. Install All Dependencies:
   ```bash
   pip install pytest pytest-django factory-boy selenium
   ```

5. Fix Import Paths:
   Make sure all test files have correct imports:
   ```python
   import pytest
   from django.test import TestCase, Client
   from django.contrib.auth import get_user_model
   from django.urls import reverse
   
   User = get_user_model()
   ```

6. URL Configuration:
   If getting reverse() errors, ensure urls.py has app_name:
   ```python
   # accounts/urls.py
   app_name = 'accounts'
   urlpatterns = [...]
   
   # orders/urls.py
   app_name = 'orders'
   urlpatterns = [...]
   ```
"""
    print(fixes)

def main():
    """Run all diagnostic checks."""
    print("🔍 Jersey Artwork Test Diagnostics")
    print("="*60)
    
    # Check Django configuration
    check_django_apps()
    
    # Check test dependencies
    check_test_dependencies()
    
    # Define test files to check
    test_files = [
        ('accounts/tests/test_forms.py', 'Accounts Forms Tests'),
        ('accounts/tests/test_views.py', 'Accounts Views Tests'),
        ('orders/tests/test_forms.py', 'Orders Forms Tests'),
        ('orders/tests/test_models/test_order.py', 'Order Model Tests'),
        ('cart/tests/test_models/test_cart.py', 'Cart Model Tests'),
    ]
    
    # Check each test file
    print("\n" + "="*60)
    print("Checking Individual Test Files")
    
    for file_path, test_name in test_files:
        if os.path.exists(file_path):
            check_import(file_path, test_name)
        else:
            print(f"\n{'='*60}")
            print(f"❌ Missing: {file_path}")
            print(f"   Create with: touch {file_path}")
    
    # Provide common fixes
    suggest_fixes_for_common_issues()
    
    print("\n" + "="*60)
    print("Diagnostic Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Fix any missing dependencies (pip install)")
    print("2. Create any missing files (forms.py, etc.)")
    print("3. Fix import errors in test files")
    print("4. Run tests again with:")
    print("   DJANGO_SETTINGS_MODULE=artworks.settings_test python -m pytest -v")

if __name__ == "__main__":
    main()
