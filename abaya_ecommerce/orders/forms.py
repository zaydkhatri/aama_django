# orders/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from users.models import Address
from .models import Order, Return, ReturnItem
from products.models import Size, Color, Fabric

class CheckoutForm(forms.Form):
    # Customer Information
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    # Shipping Address
    shipping_address_choice = forms.ChoiceField(
        choices=[('existing', 'Use an existing address'), ('new', 'Add a new address')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='existing'
    )
    existing_shipping_address = forms.UUIDField(required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    
    # New Shipping Address
    shipping_address_line1 = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_address_line2 = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_city = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_state = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_postal_code = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_country = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    save_shipping_address = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    # Billing Address
    billing_same_as_shipping = forms.BooleanField(
        required=False, 
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    billing_address_choice = forms.ChoiceField(
        choices=[('existing', 'Use an existing address'), ('new', 'Add a new address')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='existing',
        required=False
    )
    existing_billing_address = forms.UUIDField(required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    
    # New Billing Address
    billing_address_line1 = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    billing_address_line2 = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    billing_city = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    billing_state = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    billing_postal_code = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    billing_country = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    billing_phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    save_billing_address = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    # Payment
    payment_method = forms.ChoiceField(
        choices=[
            ('CREDIT_CARD', 'Credit Card'),
            ('DEBIT_CARD', 'Debit Card'),
            ('UPI', 'UPI'),
            ('NET_BANKING', 'Net Banking'),
            ('WALLET', 'Wallet'),
            ('COD', 'Cash on Delivery'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    # Coupon
    coupon_code = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    # Order Notes
    notes = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and user.is_authenticated:
            # Pre-fill user information
            self.fields['email'].initial = user.email
            self.fields['name'].initial = user.name
            self.fields['phone'].initial = user.phone
            
            # Get user addresses
            shipping_addresses = Address.objects.filter(
                user=user, 
                address_type__in=['SHIPPING', 'BOTH']
            )
            billing_addresses = Address.objects.filter(
                user=user, 
                address_type__in=['BILLING', 'BOTH']
            )
            
            # Set address choices
            shipping_choices = [(str(addr.id), f"{addr.address_line1}, {addr.city}, {addr.state}, {addr.country}") 
                               for addr in shipping_addresses]
            billing_choices = [(str(addr.id), f"{addr.address_line1}, {addr.city}, {addr.state}, {addr.country}") 
                              for addr in billing_addresses]
            
            # Update address field choices
            self.fields['existing_shipping_address'].widget = forms.Select(
                attrs={'class': 'form-control'},
                choices=[('', 'Select an address')] + shipping_choices
            )
            self.fields['existing_billing_address'].widget = forms.Select(
                attrs={'class': 'form-control'},
                choices=[('', 'Select an address')] + billing_choices
            )
            
            # Set default addresses if available
            default_shipping = shipping_addresses.filter(is_default=True).first()
            if default_shipping:
                self.fields['existing_shipping_address'].initial = str(default_shipping.id)
            
            default_billing = billing_addresses.filter(is_default=True).first()
            if default_billing:
                self.fields['existing_billing_address'].initial = str(default_billing.id)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate shipping address
        shipping_choice = cleaned_data.get('shipping_address_choice')
        if shipping_choice == 'existing':
            if not cleaned_data.get('existing_shipping_address'):
                self.add_error('existing_shipping_address', _('Please select a shipping address.'))
        else:  # new
            if not cleaned_data.get('shipping_address_line1'):
                self.add_error('shipping_address_line1', _('This field is required.'))
            if not cleaned_data.get('shipping_city'):
                self.add_error('shipping_city', _('This field is required.'))
            if not cleaned_data.get('shipping_state'):
                self.add_error('shipping_state', _('This field is required.'))
            if not cleaned_data.get('shipping_postal_code'):
                self.add_error('shipping_postal_code', _('This field is required.'))
            if not cleaned_data.get('shipping_country'):
                self.add_error('shipping_country', _('This field is required.'))
        
        # Validate billing address if not same as shipping
        billing_same = cleaned_data.get('billing_same_as_shipping')
        if not billing_same:
            billing_choice = cleaned_data.get('billing_address_choice')
            if billing_choice == 'existing':
                if not cleaned_data.get('existing_billing_address'):
                    self.add_error('existing_billing_address', _('Please select a billing address.'))
            else:  # new
                if not cleaned_data.get('billing_address_line1'):
                    self.add_error('billing_address_line1', _('This field is required.'))
                if not cleaned_data.get('billing_city'):
                    self.add_error('billing_city', _('This field is required.'))
                if not cleaned_data.get('billing_state'):
                    self.add_error('billing_state', _('This field is required.'))
                if not cleaned_data.get('billing_postal_code'):
                    self.add_error('billing_postal_code', _('This field is required.'))
                if not cleaned_data.get('billing_country'):
                    self.add_error('billing_country', _('This field is required.'))
        
        return cleaned_data


class CouponForm(forms.Form):
    code = forms.CharField(
        label=_('Coupon code'),
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your coupon code'})
    )


class ReturnForm(forms.ModelForm):
    class Meta:
        model = Return
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ReturnItemForm(forms.ModelForm):
    class Meta:
        model = ReturnItem
        fields = ['product', 'size', 'color', 'fabric', 'quantity', 'reason', 'condition']
        widgets = {
            'product': forms.HiddenInput(),
            'size': forms.HiddenInput(),
            'color': forms.HiddenInput(),
            'fabric': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'condition': forms.TextInput(attrs={'class': 'form-control'}),
        }


class OrderFilterForm(forms.Form):
    ORDER_STATUS_CHOICES = [('', 'All')] + list(Order.ORDER_STATUS_CHOICES)
    
    status = forms.ChoiceField(
        required=False,
        choices=ORDER_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    order_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by order number'})
    )