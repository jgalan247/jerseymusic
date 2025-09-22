with open('orders/forms.py', 'r') as f:
    content = f.read()

# Find and replace the save method
old_save = '''    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.order:
            instance.order = self.order
            instance.requested_by = self.order.user
            instance.refund_amount = self.order.total
        if commit:
            instance.save()
        return instance'''

new_save = '''    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.order:
            instance.order = self.order
            instance.customer = self.order.user
            # Get artist from first order item
            first_item = self.order.items.first()
            if first_item and first_item.artwork:
                instance.artist = first_item.artwork.artist
        if commit:
            instance.save()
        return instance'''

content = content.replace(old_save, new_save)

with open('orders/forms.py', 'w') as f:
    f.write(content)
    
print("Fixed RefundRequestForm save method")
