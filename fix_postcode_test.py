with open('orders/tests/test_forms/test_checkout.py', 'r') as f:
    content = f.read()

# Remove JE24UH from invalid_postcodes list
content = content.replace(
    "'JE24UH',   # Missing space (if space required)",
    "# 'JE24UH' removed - now valid without space"
)

with open('orders/tests/test_forms/test_checkout.py', 'w') as f:
    f.write(content)

print("Updated test to allow JE24UH as valid")
