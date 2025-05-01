from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.contrib.auth.hashers import make_password
import datetime
import uuid

from users.models import User, Address, NotificationPreference, Session
from orders.models import Order
from dashboard.forms import UserForm
from dashboard.models import DashboardActivity


@login_required
def user_list(request):
    """List all users with search and filter functionality"""
    # Get filter parameters
    search = request.GET.get('search', '')
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    verified = request.GET.get('verified', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    users = User.objects.all()
    
    # Apply filters
    if search:
        users = users.filter(
            Q(email__icontains=search) | 
            Q(name__icontains=search) | 
            Q(phone__icontains=search)
        )
    
    if role:
        users = users.filter(role=role)
    
    if status:
        is_active = status == 'active'
        users = users.filter(is_active=is_active)
    
    if verified:
        is_verified = verified == 'yes'
        users = users.filter(is_email_verified=is_verified)
    
    if date_from:
        try:
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            users = users.filter(created_at__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    
    if date_to:
        try:
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            users = users.filter(created_at__date__lte=date_to)
        except (ValueError, TypeError):
            pass
    
    # Annotate with order count and total spent
    users = users.annotate(
        order_count=Count('orders', distinct=True),
        total_spent=Sum('orders__total')
    )
    
    # Ordering
    order_by = request.GET.get('order_by', '-created_at')
    valid_order_fields = [
        'email', '-email', 'name', '-name', 'created_at', '-created_at',
        'order_count', '-order_count', 'total_spent', '-total_spent'
    ]
    
    if order_by in valid_order_fields:
        users = users.order_by(order_by)
    else:
        users = users.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(users, 20)
    page = request.GET.get('page')
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
    
    # Get user stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    admins = User.objects.filter(role='ADMIN').count()
    staff = User.objects.filter(role='STAFF').count()
    customers = User.objects.filter(role='CUSTOMER').count()
    
    # New users in last 30 days
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    new_users_30d = User.objects.filter(created_at__gte=thirty_days_ago).count()
    
    context = {
        'users': users,
        'total_users': total_users,
        'active_users': active_users,
        'admins': admins,
        'staff': staff,
        'customers': customers,
        'new_users_30d': new_users_30d,
        'role_choices': User.ROLE_CHOICES,
        'filters': {
            'search': search,
            'role': role,
            'status': status,
            'verified': verified,
            'date_from': date_from,
            'date_to': date_to,
            'order_by': order_by
        }
    }
    
    return render(request, 'dashboard/users/list.html', context)


@login_required
def user_create(request):
    """Create a new user"""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            # Create user but don't save yet
            user = form.save(commit=False)
            
            # Generate a random password if not provided
            if not request.POST.get('password'):
                temp_password = uuid.uuid4().hex[:8]
                user.password = make_password(temp_password)
                temp_password_created = True
            else:
                user.password = make_password(request.POST.get('password'))
                temp_password_created = False
            
            # Save the user
            user.save()
            
            # Create notification preferences
            NotificationPreference.objects.create(user=user)
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Created user',
                entity_type='User',
                entity_id=str(user.id),
                details={
                    'email': user.email,
                    'name': user.name,
                    'role': user.role,
                    'temp_password_created': temp_password_created
                }
            )
            
            if temp_password_created:
                messages.success(
                    request, 
                    f'User {user.name} created successfully with temporary password: {temp_password}'
                )
            else:
                messages.success(request, f'User {user.name} created successfully.')
            
            # Redirect based on the "save_action" parameter
            save_action = request.POST.get('save_action', 'save')
            if save_action == 'save_and_add_another':
                return redirect('dashboard:user_create')
            else:
                return redirect('dashboard:user_list')
    else:
        form = UserForm()
    
    context = {
        'form': form,
        'title': 'Create User'
    }
    
    return render(request, 'dashboard/users/create.html', context)


@login_required
def user_detail(request, pk):
    """Display user details"""
    user = get_object_or_404(User, pk=pk)
    
    # Get user's addresses
    addresses = Address.objects.filter(user=user)
    
    # Get user's orders
    orders = Order.objects.filter(user=user).order_by('-created_at')
    
    # Get active sessions
    sessions = Session.objects.filter(user=user, expires_at__gt=timezone.now())
    
    # Get notification preferences
    try:
        notification_prefs = NotificationPreference.objects.get(user=user)
    except NotificationPreference.DoesNotExist:
        notification_prefs = None
    
    # Calculate some stats
    total_orders = orders.count()
    total_spent = orders.aggregate(total=Sum('total'))['total'] or 0
    avg_order_value = total_spent / total_orders if total_orders > 0 else 0
    
    # Get recent activity (could be from a custom user activity model if you have one)
    # For this example, we'll just use orders as activity
    recent_activities = orders[:10]
    
    context = {
        'user_obj': user,  # Use user_obj to avoid name conflict
        'addresses': addresses,
        'orders': orders[:10],  # Show only latest 10 orders
        'sessions': sessions,
        'notification_prefs': notification_prefs,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'avg_order_value': avg_order_value,
        'recent_activities': recent_activities
    }
    
    return render(request, 'dashboard/users/detail.html', context)


@login_required
def user_edit(request, pk):
    """Edit an existing user"""
    user = get_object_or_404(User, pk=pk)
    
    # Prevent non-admin users from editing admin users
    if user.role == 'ADMIN' and request.user.role != 'ADMIN':
        messages.error(request, 'You do not have permission to edit admin users.')
        return redirect('dashboard:user_list')
    
    if request.method == 'POST':
        # Special handling for password
        reset_password = request.POST.get('reset_password') == 'yes'
        
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            # Track changes for activity log
            changed_fields = []
            for field in form.changed_data:
                orig_value = getattr(user, field) if hasattr(user, field) else None
                changed_fields.append({
                    'field': field,
                    'old': str(orig_value),
                    'new': str(form.cleaned_data.get(field))
                })
            
            # Save the user
            updated_user = form.save(commit=False)
            
            # Handle password reset if requested
            if reset_password:
                temp_password = uuid.uuid4().hex[:8]
                updated_user.password = make_password(temp_password)
                
                # Add to changed fields
                changed_fields.append({
                    'field': 'password',
                    'old': 'Hidden for security',
                    'new': 'Reset to temporary password'
                })
            
            updated_user.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated user',
                entity_type='User',
                entity_id=str(user.id),
                details={
                    'email': user.email,
                    'name': user.name,
                    'changes': changed_fields,
                    'password_reset': reset_password
                }
            )
            
            if reset_password:
                messages.success(
                    request, 
                    f'User {updated_user.name} updated successfully. ' +
                    f'New temporary password: {temp_password}'
                )
            else:
                messages.success(request, f'User {updated_user.name} updated successfully.')
            
            return redirect('dashboard:user_detail', pk=user.id)
    else:
        form = UserForm(instance=user)
    
    context = {
        'form': form,
        'user_obj': user,
        'title': f'Edit User: {user.name}'
    }
    
    return render(request, 'dashboard/users/edit.html', context)