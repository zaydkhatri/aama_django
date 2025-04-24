# payments/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import PaymentMethod, Refund

class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['type', 'card_last_four', 'card_brand', 'card_exp_month', 'card_exp_year', 
                  'upi_id', 'wallet_provider', 'is_default']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'card_last_four': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 4}),
            'card_brand': forms.TextInput(attrs={'class': 'form-control'}),
            'card_exp_month': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'card_exp_year': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 4}),
            'upi_id': forms.TextInput(attrs={'class': 'form-control'}),
            'wallet_provider': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make fields conditionally required based on payment type
        self.fields['card_last_four'].required = False
        self.fields['card_brand'].required = False
        self.fields['card_exp_month'].required = False
        self.fields['card_exp_year'].required = False
        self.fields['upi_id'].required = False
        self.fields['wallet_provider'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('type')
        
        # Validate card details
        if payment_type in ['CREDIT_CARD', 'DEBIT_CARD']:
            card_last_four = cleaned_data.get('card_last_four')
            card_brand = cleaned_data.get('card_brand')
            card_exp_month = cleaned_data.get('card_exp_month')
            card_exp_year = cleaned_data.get('card_exp_year')
            
            if not card_last_four:
                self.add_error('card_last_four', _('This field is required for card payments.'))
            
            if not card_brand:
                self.add_error('card_brand', _('This field is required for card payments.'))
            
            if not card_exp_month:
                self.add_error('card_exp_month', _('This field is required for card payments.'))
            elif not card_exp_month.isdigit() or int(card_exp_month) < 1 or int(card_exp_month) > 12:
                self.add_error('card_exp_month', _('Please enter a valid month (1-12).'))
            
            if not card_exp_year:
                self.add_error('card_exp_year', _('This field is required for card payments.'))
            elif not card_exp_year.isdigit() or len(card_exp_year) != 4:
                self.add_error('card_exp_year', _('Please enter a valid 4-digit year.'))
        
        # Validate UPI ID
        elif payment_type == 'UPI':
            upi_id = cleaned_data.get('upi_id')
            
            if not upi_id:
                self.add_error('upi_id', _('This field is required for UPI payments.'))
            elif '@' not in upi_id:
                self.add_error('upi_id', _('Please enter a valid UPI ID (e.g., name@upi).'))
        
        # Validate wallet provider
        elif payment_type == 'WALLET':
            wallet_provider = cleaned_data.get('wallet_provider')
            
            if not wallet_provider:
                self.add_error('wallet_provider', _('This field is required for wallet payments.'))
        
        return cleaned_data


class RefundForm(forms.Form):
    reason = forms.CharField(
        label=_('Reason for Refund'),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text=_('Please provide a reason for requesting this refund.')
    )


class GatewaySelectionForm(forms.Form):
    gateway = forms.ChoiceField(
        label=_('Select Payment Method'),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        gateways = kwargs.pop('gateways', [])
        super().__init__(*args, **kwargs)
        
        # Set gateway choices
        self.fields['gateway'].choices = [
            (g['id'], g['name']) for g in gateways
        ]