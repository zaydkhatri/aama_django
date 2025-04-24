# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.utils.translation import gettext_lazy as _
from .models import User, Address, NotificationPreference

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    name = forms.CharField(
        label=_("Full Name"),
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'})
    )
    phone = forms.CharField(
        label=_("Phone Number"),
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'})
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        label=_("Password Confirmation"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    
    class Meta:
        model = User
        fields = ('email', 'name', 'phone', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    
    error_messages = {
        'invalid_login': _(
            "Please enter a correct email and password. Note that both "
            "fields may be case-sensitive."
        ),
        'inactive': _("This account is inactive."),
    }

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
    )

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'is_default', 'address_type', 'phone_number'
        ]
        widgets = {
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address_type': forms.Select(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            'email_marketing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_order_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_returns': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_account': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_marketing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_order_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_returns': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_account': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['name', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }