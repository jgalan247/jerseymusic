#!/usr/bin/env python
"""
Quick fix script to patch test files with correct parish values.
Run: python fix_tests.py
"""

import os

def fix_parish_values_in_tests():
    """Fix parish values in test files."""
    
    # Map of wrong values to correct values
    replacements = {
        "'St. Helier'": "'st_helier'",
        "'St. Brelade'": "'st_brelade'",
        "'St. Clement'": "'st_clement'",
        "'St. John'": "'st_john'",
        "'St. Lawrence'": "'st_lawrence'",
        "'St. Martin'": "'st_martin'",
        "'St. Mary'": "'st_mary'",
        "'St. Ouen'": "'st_ouen'",
        "'St. Peter'": "'st_peter'",
        "'St. Saviour'": "'st_saviour'",
        "'Grouville'": "'grouville'",
        "'Trinity'": "'trinity'",
    }
    
    # Files to fix
    test_files = [
        'accounts/tests/test_forms.py',
        'orders/tests/test_forms.py',
        'orders/tests/test_forms/test_checkout.py',
    ]
    
    for filepath in test_files:
        if os.path.exists(filepath):
            print(f"Fixing {filepath}...")
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            original = content
            for old, new in replacements.items():
                content = content.replace(old, new)
            
            if content != original:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"  ✅ Fixed parish values")
            else:
                print(f"  ℹ️  No changes needed")
    
    print("\nDone! Now run your tests again.")

if __name__ == '__main__':
    fix_parish_values_in_tests()
