# Fix the test assertions now that the model is working correctly
with open('accounts/tests/test_models/test_user.py', 'r') as f:
    content = f.read()

# Fix test_active_artworks_property - should expect 1 active artwork
content = content.replace(
    "self.assertEqual(profile.active_artworks, 0)  # Bug in model",
    "self.assertEqual(profile.active_artworks, 1)  # Fixed - now returns correct count"
)

# Fix test_total_artworks_property - should expect 3 artworks
content = content.replace(
    "self.assertEqual(profile.total_artworks, 0)  # Bug in model",
    "self.assertEqual(profile.total_artworks, 3)  # Fixed - now returns correct count"
)

with open('accounts/tests/test_models/test_user.py', 'w') as f:
    f.write(content)

print("Updated tests to match the fixed model behavior")
