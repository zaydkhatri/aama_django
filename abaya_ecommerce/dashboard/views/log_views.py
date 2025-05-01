# dashboard/views/log_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse

from dashboard.models import ActivityLogEntry, DashboardSetting
from dashboard.utils import staff_member_required, log_admin_activity, paginate_queryset

@staff_member_required
def activity_logs(request):
    """Display activity logs with filtering options."""
    # Get all activity logs
    logs = ActivityLogEntry.objects.all().order_by('-created_at')
    
    # Apply filters
    # User filter
    user_id = request.GET.get('user')
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    # Action filter
    action = request.GET.get('action')
    if action:
        logs = logs.filter(action=action)
    
    # Entity type filter
    entity_type = request.GET.get('entity_type')
    if entity_type:
        logs = logs.filter(entity_type=entity_type)
    
    # Date range filters
    date_from = request.GET.get('date_from')
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)
    
    # Search filter
    search = request.GET.get('search')
    if search:
        logs = logs.filter(
            Q(description__icontains=search) |
            Q(entity_id__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Paginate results
    logs = paginate_queryset(request, logs, 50)
    
    # Get unique users, actions, and entity types for filter dropdowns
    unique_users = ActivityLogEntry.objects.values_list('user_id', 'user__email').distinct()
    unique_actions = ActivityLogEntry.objects.values_list('action', flat=True).distinct()
    unique_entity_types = ActivityLogEntry.objects.values_list('entity_type', flat=True).distinct()
    
    return render(request, 'dashboard/logs/activity_logs.html', {
        'logs': logs,
        'unique_users': unique_users,
        'unique_actions': unique_actions,
        'unique_entity_types': unique_entity_types,
        'filters': {
            'user': user_id,
            'action': action,
            'entity_type': entity_type,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    })

@staff_member_required
def dashboard_settings(request):
    """Manage dashboard settings."""
    if request.method == 'POST':
        # Handle settings update
        setting_id = request.POST.get('setting_id')
        setting_value = request.POST.get('value')
        
        if setting_id and setting_value is not None:
            setting = get_object_or_404(DashboardSetting, id=setting_id)
            setting.value = setting_value
            setting.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'UPDATE',
                'DashboardSetting',
                setting.id,
                f"Updated dashboard setting '{setting.key}'",
                request
            )
            
            messages.success(request, f"Setting '{setting.key}' has been updated successfully.")
            return redirect('dashboard:settings')
    
    # Group settings by their group keys for display
    all_settings = DashboardSetting.objects.all().order_by('key')
    grouped_settings = {}
    
    for setting in all_settings:
        group = setting.key.split('.')[0] if '.' in setting.key else 'General'
        if group not in grouped_settings:
            grouped_settings[group] = []
        grouped_settings[group].append(setting)
    
    return render(request, 'dashboard/settings/settings.html', {
        'grouped_settings': grouped_settings,
    })