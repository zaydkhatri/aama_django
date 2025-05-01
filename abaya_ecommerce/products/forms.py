# products/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Review, Size, Color, Fabric, Product
from .widgets import MultipleFileInput  # Import the custom widget

class ProductFilterForm(forms.Form):
    category = forms.UUIDField(required=False, widget=forms.HiddenInput())
    min_price = forms.DecimalField(required=False, min_value=0, 
                                   widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Price'}))
    max_price = forms.DecimalField(required=False, min_value=0, 
                                   widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Price'}))
    size = forms.ModelChoiceField(
        queryset=Size.objects.filter(is_active=True),
        required=False,
        empty_label="All Sizes",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    color = forms.ModelChoiceField(
        queryset=Color.objects.filter(is_active=True),
        required=False,
        empty_label="All Colors",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fabric = forms.ModelChoiceField(
        queryset=Fabric.objects.filter(is_active=True),
        required=False,
        empty_label="All Fabrics",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
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

class ProductVariantForm(forms.Form):
    """Form for selecting product variants (size, color, fabric)"""
    size = forms.ModelChoiceField(
        queryset=Size.objects.filter(is_active=True),
        widget=forms.RadioSelect,
        required=True,
        empty_label=None
    )
    color = forms.ModelChoiceField(
        queryset=Color.objects.filter(is_active=True),
        widget=forms.RadioSelect,
        required=True,
        empty_label=None
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    
    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        
        # Don't filter sizes - show all active sizes
        self.fields['size'].queryset = Size.objects.filter(is_active=True)
            
        if product:
            # Filter colors to those available for this product's fabrics
            available_fabrics = Fabric.objects.filter(products=product)
            self.fields['color'].queryset = Color.objects.filter(
                is_active=True,
                fabrics__in=available_fabrics
            ).distinct()

class ReviewForm(forms.ModelForm):
    # Use the custom MultipleFileInput widget for multiple file uploads
    images = forms.FileField(
        required=False,
        widget=MultipleFileInput(attrs={'class': 'form-control'}),
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