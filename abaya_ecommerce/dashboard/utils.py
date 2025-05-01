# dashboard/utils.py
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import ActivityLogEntry

def log_admin_activity(user, action, entity_type, entity_id=None, description=None, request=None):
    """
    Log admin activity in the dashboard.
    
    Args:
        user: User who performed the action
        action: Type of action (from ActivityLogEntry.ACTION_CHOICES)
        entity_type: Type of entity affected (e.g., 'Product', 'Category')
        entity_id: ID of the entity (optional)
        description: Description of the action (optional)
        request: The HTTP request (optional, for IP and user agent)
    """
    entry = ActivityLogEntry(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id if entity_id else "",
        description=description if description else f"{action} on {entity_type}"
    )
    
    if request:
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            entry.ip_address = x_forwarded_for.split(',')[0]
        else:
            entry.ip_address = request.META.get('REMOTE_ADDR')
            
        # Get user agent
        entry.user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    entry.save()
    return entry

def is_staff_or_admin(user):
    """Check if user is staff or admin."""
    return user.is_authenticated and (user.is_staff or user.role == 'ADMIN')

def staff_member_required(view_func):
    """Decorator for views that require staff or admin status."""
    return user_passes_test(is_staff_or_admin)(view_func)

class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin for class-based views that require staff or admin status."""
    def test_func(self):
        return is_staff_or_admin(self.request.user)

def paginate_queryset(request, queryset, per_page=10):
    """
    Paginate a queryset for use in a view.
    
    Args:
        request: The HTTP request
        queryset: The queryset to paginate
        per_page: Number of items per page
        
    Returns:
        Paginated queryset page
    """
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page')
    
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        items = paginator.page(paginator.num_pages)
        
    return items