# Create this file as products/widgets.py
from django import forms

class MultipleFileInput(forms.ClearableFileInput):
    """
    A custom widget that allows for multiple file uploads.
    """
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs['multiple'] = 'multiple'
        super().__init__(attrs)