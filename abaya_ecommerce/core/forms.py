# core/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _

class ContactForm(forms.Form):
    name = forms.CharField(
        label=_('Name'),
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'})
    )
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your.email@example.com'})
    )
    subject = forms.CharField(
        label=_('Subject'),
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Message Subject'})
    )
    message = forms.CharField(
        label=_('Message'),
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Message', 'rows': 5})
    )


class NewsletterForm(forms.Form):
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your.email@example.com'})
    )
    name = forms.CharField(
        label=_('Name'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name (Optional)'})
    )


class SettingForm(forms.Form):
    value = forms.CharField(
        label=_('Value'),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    def __init__(self, *args, **kwargs):
        setting_type = kwargs.pop('setting_type', 'TEXT')
        super().__init__(*args, **kwargs)
        
        # Adjust field based on setting type
        if setting_type == 'BOOLEAN':
            self.fields['value'] = forms.BooleanField(
                label=_('Value'),
                required=False,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )
        elif setting_type == 'NUMBER':
            self.fields['value'] = forms.DecimalField(
                label=_('Value'),
                widget=forms.NumberInput(attrs={'class': 'form-control'})
            )
        elif setting_type == 'HTML':
            self.fields['value'].widget.attrs.update({'class': 'form-control richtext-editor'})