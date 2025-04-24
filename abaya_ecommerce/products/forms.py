# products/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Review

class ProductFilterForm(forms.Form):
    category = forms.UUIDField(required=False, widget=forms.HiddenInput())
    min_price = forms.DecimalField(required=False, min_value=0, 
                                   widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Price'}))
    max_price = forms.DecimalField(required=False, min_value=0, 
                                   widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Price'}))
    sort = forms.ChoiceField(required=False, choices=[
        ('', 'Default'),
        ('price_low', 'Price Low to High'),
        ('price_high', 'Price High to Low'),
        ('newest', 'Newest First'),
        ('rating', 'Highest Rated'),
        ('popularity', 'Most Popular'),
    ], widget=forms.Select(attrs={'class': 'form-control'}))
    
    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            self.add_error('max_price', _('Maximum price must be greater than minimum price.'))
        
        return cleaned_data

class ReviewForm(forms.ModelForm):
    images = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Review
        fields = ['rating', 'title', 'review']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5,
                'step': 1
            }),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Review Title'}),
            'review': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write your review here...', 'rows': 4})
        }

class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search products...'})
    )