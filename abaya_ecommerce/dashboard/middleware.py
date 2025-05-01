from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings

class DashboardAccessMiddleware:
    """
    Middleware to restrict access to dashboard
    Only ADMIN and STAFF users can access the dashboard
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Process only dashboard URLs
        if request.path.startswith('/dashboard/') and not request.path.startswith('/dashboard/login'):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to access the dashboard.')
                return redirect(f"{reverse('dashboard:login')}?next={request.path}")
            
            # Check if user has appropriate role (ADMIN or STAFF)
            if not (request.user.is_admin() or request.user.is_staff_member()):
                messages.error(request, 'You do not have permission to access the dashboard.')
                return redirect('home')
        
        response = self.get_response(request)
        return response


class DashboardActivityMiddleware:
    """
    Middleware to log admin activities in dashboard
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Process only dashboard URLs for authenticated admin/staff users
        # Skip for static files, GET requests, and login/logout
        if (request.path.startswith('/dashboard/') and 
            request.method != 'GET' and 
            not request.path.endswith(('.js', '.css', '.png', '.jpg', '.jpeg', '.gif')) and
            not any(path in request.path for path in ['/login/', '/logout/']) and
            request.user.is_authenticated and
            (request.user.is_admin() or request.user.is_staff_member())):
            
            # Import here to avoid circular imports
            from .models import DashboardActivity
            
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            # Determine action and entity from URL pattern
            action, entity_type, entity_id = self._parse_request_info(request)
            
            if action and entity_type:
                # Create activity log
                DashboardActivity.objects.create(
                    user=request.user,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id or '',
                    ip_address=ip,
                    details={
                        'path': request.path,
                        'method': request.method,
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')
                    }
                )
        
        return response
    
    def _parse_request_info(self, request):
        """Parse request path to determine action, entity type and ID"""
        path_parts = request.path.strip('/').split('/')
        
        # Skip if not enough parts in path
        if len(path_parts) < 3:
            return None, None, None
        
        # Example: dashboard/products/edit/uuid
        if len(path_parts) >= 4:
            if path_parts[2] == 'create':
                return 'Created', path_parts[1].rstrip('s').capitalize(), None
            elif path_parts[2] == 'edit':
                return 'Updated', path_parts[1].rstrip('s').capitalize(), path_parts[3]
            elif path_parts[2] == 'delete':
                return 'Deleted', path_parts[1].rstrip('s').capitalize(), path_parts[3]
        
        return None, None, None