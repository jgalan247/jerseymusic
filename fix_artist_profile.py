# Fix ArtistProfile model
with open('accounts/models.py', 'r') as f:
    content = f.read()

# Fix line 92
content = content.replace(
    "return self.artworks.count()",
    "return self.user.artworks.count()"
)

# Fix line 97
content = content.replace(
    "return self.artworks.filter(status='active').count()",
    "return self.user.artworks.filter(status='active').count()"
)

with open('accounts/models.py', 'w') as f:
    f.write(content)

print("Fixed ArtistProfile properties")
