from django.shortcuts import render

# Create your views here.
# users/views.py
import uuid
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction

from orders.models import Order
from carts.models import Wishlist

from .models import User, Address, NotificationPreference, Session
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordResetForm,
    CustomSetPasswordForm, AddressForm, NotificationPreferenceForm, ProfileUpdateForm
)

def register(request):
    if request.user.is_authenticated:
        return redirect('account_dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.is_active = True
                user.is_email_verified = False
                user.email_verification_token = uuid.uuid4().hex
                user.email_verification_expiry = timezone.now() + timedelta(days=2)
                user.save()
                
                # Create notification preferences
                NotificationPreference.objects.create(user=user)
                
                # Send verification email
                send_verification_email(request, user)
                
                messages.success(
                    request, 
                    'Your account has been created! Please check your email to verify your account.'
                )
                return redirect('login')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('account_dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if not user.is_email_verified:
                    messages.error(
                        request, 
                        'Please verify your email address before logging in. '
                        'Check your inbox for the verification link.'
                    )
                    return redirect('login')
                
                if user.is_locked_out():
                    messages.error(
                        request, 
                        'Your account is temporarily locked due to too many failed login attempts. '
                        'Please try again later.'
                    )
                    return redirect('login')
                
                login(request, user)
                user.reset_login_attempts()
                
                # Record login session
                session = Session.objects.create(
                    user=user,
                    token=request.session.session_key,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    ip_address=get_client_ip(request),
                    expires_at=timezone.now() + timedelta(days=1)
                )
                
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                # Redirect to next parameter or dashboard
                next_page = request.GET.get('next', reverse('account_dashboard'))
                return redirect(next_page)
            else:
                try:
                    user = User.objects.get(email=email)
                    user.increment_login_attempts()
                except User.DoesNotExist:
                    pass
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        # Invalidate current session
        if request.session.session_key:
            Session.objects.filter(token=request.session.session_key).delete()
        logout(request)
    
    return redirect('login')

def verify_email(request, token):
    user = get_object_or_404(User, email_verification_token=token)
    
    if user.email_verification_expiry and timezone.now() > user.email_verification_expiry:
        messages.error(request, 'Email verification link has expired. Please request a new one.')
        return redirect('resend_verification')
    
    user.is_email_verified = True
    user.email_verification_token = None
    user.email_verification_expiry = None
    user.save()
    
    messages.success(request, 'Your email has been verified! You can now log in.')
    return redirect('login')

def resend_verification(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email, is_email_verified=False)
            user.email_verification_token = uuid.uuid4().hex
            user.email_verification_expiry = timezone.now() + timedelta(days=2)
            user.save()
            
            send_verification_email(request, user)
            
            messages.success(
                request, 
                'A new verification email has been sent to your email address.'
            )
            return redirect('login')
        except User.DoesNotExist:
            messages.error(
                request, 
                'No unverified account found with this email address.'
            )
    
    return render(request, 'users/resend_verification.html')

def password_reset_request(request):
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                user.password_reset_token = uuid.uuid4().hex
                user.password_reset_expiry = timezone.now() + timedelta(hours=24)
                user.save()
                
                send_password_reset_email(request, user)
                
                messages.success(
                    request, 
                    'Password reset link has been sent to your email address.'
                )
                return redirect('login')
            except User.DoesNotExist:
                messages.error(
                    request, 
                    'No account found with this email address.'
                )
    else:
        form = CustomPasswordResetForm()
    
    return render(request, 'users/password_reset_request.html', {'form': form})

def password_reset_confirm(request, token):
    user = get_object_or_404(User, password_reset_token=token)
    
    if user.password_reset_expiry and timezone.now() > user.password_reset_expiry:
        messages.error(request, 'Password reset link has expired. Please request a new one.')
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = CustomSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            user.password_reset_token = None
            user.password_reset_expiry = None
            user.save()
            
            messages.success(
                request, 
                'Your password has been reset! You can now log in with your new password.'
            )
            return redirect('login')
    else:
        form = CustomSetPasswordForm(user)
    
    return render(request, 'users/password_reset_confirm.html', {'form': form})

@login_required
def account_dashboard(request):
    addresses = Address.objects.filter(user=request.user)
    notification_prefs = NotificationPreference.objects.get_or_create(user=request.user)[0]
    
    # For orders
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    for order in recent_orders:
        for item in order.items.all():
            item.product.default_image = item.product.get_default_image()
    
    # For wishlist items
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        for item in wishlist.items.all():
            item.product.default_image = item.product.get_default_image()
    except Wishlist.DoesNotExist:
        wishlist = None
    
    return render(request, 'users/dashboard.html', {
        'user': request.user,
        'addresses': addresses,
        'notification_prefs': notification_prefs,
        'recent_orders': recent_orders,
        'wishlist': wishlist
    })

@login_required
def profile_update(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('account_dashboard')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'users/profile_update.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomSetPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('account_dashboard')
    else:
        form = CustomSetPasswordForm(request.user)
    
    return render(request, 'users/change_password.html', {'form': form})

@login_required
def manage_addresses(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'users/manage_addresses.html', {'addresses': addresses})

@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Address added successfully.')
            return redirect('manage_addresses')
    else:
        form = AddressForm()
    
    return render(request, 'users/address_form.html', {'form': form, 'title': 'Add Address'})

@login_required
def edit_address(request, uuid):
    address = get_object_or_404(Address, id=uuid, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully.')
            return redirect('manage_addresses')
    else:
        form = AddressForm(instance=address)
    
    return render(request, 'users/address_form.html', {'form': form, 'title': 'Edit Address'})

@login_required
def delete_address(request, uuid):
    address = get_object_or_404(Address, id=uuid, user=request.user)
    
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully.')
        return redirect('manage_addresses')
    
    return render(request, 'users/delete_address.html', {'address': address})

@login_required
def notification_preferences(request):
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences updated successfully.')
            return redirect('account_dashboard')
    else:
        form = NotificationPreferenceForm(instance=preferences)
    
    return render(request, 'users/notification_preferences.html', {'form': form})

@login_required
def active_sessions(request):
    current_session_key = request.session.session_key
    sessions = Session.objects.filter(user=request.user)
    
    for session in sessions:
        session.is_current = session.token == current_session_key
    
    return render(request, 'users/active_sessions.html', {'sessions': sessions})

@login_required
def end_session(request, uuid):
    if request.method == 'POST':
        session = get_object_or_404(Session, id=uuid, user=request.user)
        
        # If ending current session, logout
        if session.token == request.session.session_key:
            session.delete()
            logout(request)
            messages.success(request, 'Your current session has been ended. You have been logged out.')
            return redirect('login')
        
        # Otherwise just delete the session
        session.delete()
        messages.success(request, 'The session has been ended successfully.')
        return redirect('active_sessions')
    
    return redirect('active_sessions')

# Helper functions
def send_verification_email(request, user):
    current_site = get_current_site(request)
    subject = 'Verify Your Email Address'
    message = render_to_string('users/emails/email_verification.html', {
        'user': user,
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': current_site.domain,
        'token': user.email_verification_token,
    })
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=message
    )

def send_password_reset_email(request, user):
    current_site = get_current_site(request)
    subject = 'Reset Your Password'
    message = render_to_string('users/emails/password_reset.html', {
        'user': user,
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': current_site.domain,
        'token': user.password_reset_token,
    })
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=message
    )

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip