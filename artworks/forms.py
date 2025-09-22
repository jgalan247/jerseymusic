# artworks/forms.py - Minimal version
from django import forms
from artworks.models import Artwork

class ArtworkUploadForm(forms.ModelForm):
    class Meta:
        model = Artwork
        fields = ['title', 'description', 'price', 'main_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'main_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }