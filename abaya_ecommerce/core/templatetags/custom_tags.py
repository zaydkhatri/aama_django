# core/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """
    Template tag to replace a parameter in the current URL.
    Used for maintaining filter parameters during pagination.
    
    Usage: {% url_replace request 'page' 2 %}
    """
    query_dict = request.GET.copy()
    query_dict[field] = value
    
    return query_dict.urlencode()