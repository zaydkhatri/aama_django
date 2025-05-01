from django import forms
from products.models import Category, Product, Size, Color, Fabric, ProductMedia
from orders.models import Order, OrderItem, Return
from users.models import User, Address
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class DashboardLoginForm(AuthenticationForm):
    """Custom login form for dashboard"""
    username = forms.EmailField(
        label=_("Email"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class CategoryForm(forms.ModelForm):
    """Form for Category management"""
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'parent', 'is_active', 'image',
                  'meta_title', 'meta_description', 'meta_keywords']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'meta_keywords': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ProductForm(forms.ModelForm):
    """Form for Product management"""
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        required=True
    )
    sizes = forms.ModelMultipleChoiceField(
        queryset=Size.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        required=False
    )
    fabrics = forms.ModelMultipleChoiceField(
        queryset=Fabric.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        required=False
    )
    
    class Meta:
        model = Product
        fields = ['name', 'slug', 'description', 'sku', 'is_active', 'is_featured',
                  'price', 'sale_price', 'categories', 'sizes', 'fabrics',
                  'meta_title', 'meta_description', 'meta_keywords']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control richtext', 'rows': 4}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'meta_keywords': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ProductMediaForm(forms.ModelForm):
    """Form for Product Media management"""
    class Meta:
        model = ProductMedia
        fields = ['file', 'type', 'alt', 'is_default', 'sort_order']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'alt': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ProductVariantForm(forms.Form):
    """Form for managing product variants (sizes, colors, fabrics)"""
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.HiddenInput()
    )
    size = forms.ModelChoiceField(
        queryset=Size.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    fabric = forms.ModelChoiceField(
        queryset=Fabric.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    colors = forms.ModelMultipleChoiceField(
        queryset=Color.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        required=False,
        help_text='Select colors available for this fabric'
    )
    is_default = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Set as default fabric'
    )


class SizeForm(forms.ModelForm):
    """Form for Size management"""
    class Meta:
        model = Size
        fields = ['name', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ColorForm(forms.ModelForm):
    """Form for Color management"""
    class Meta:
        model = Color
        fields = ['name', 'color_code', 'image', 'is_active', 'fabrics']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'color_code': forms.TextInput(attrs={'class': 'form-control colorpicker'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fabrics': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        }


class FabricForm(forms.ModelForm):
    """Form for Fabric management"""
    class Meta:
        model = Fabric
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class OrderEditForm(forms.ModelForm):
    """Form for Order editing"""
    class Meta:
        model = Order
        fields = ['status', 'payment_status', 'shipping_amount', 'tax_amount', 
                  'discount_amount', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
            'shipping_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class OrderStatusForm(forms.Form):
    """Form for updating order status"""
    status = forms.ChoiceField(
        choices=Order.ORDER_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add notes about this status change'})
    )


class ReturnStatusForm(forms.Form):
    """Form for updating return status"""
    status = forms.ChoiceField(
        choices=Return.RETURN_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    refund_status = forms.ChoiceField(
        choices=Return.REFUND_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add notes about this status change'})
    )


class UserForm(forms.ModelForm):
    """Form for User management"""
    class Meta:
        model = User
        fields = ['email', 'name', 'phone', 'role', 'is_active', 'is_staff', 'is_email_verified']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_email_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DateRangeFilterForm(forms.Form):
    """Form for filtering reports by date range"""
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )