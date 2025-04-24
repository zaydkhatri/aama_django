# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    
    # Password reset
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # Account management
    path('dashboard/', views.account_dashboard, name='account_dashboard'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Address management
    path('addresses/', views.manage_addresses, name='manage_addresses'),
    path('addresses/add/', views.add_address, name='add_address'),
    path('addresses/edit/<uuid:uuid>/', views.edit_address, name='edit_address'),
    path('addresses/delete/<uuid:uuid>/', views.delete_address, name='delete_address'),
    
    # Notification preferences
    path('notifications/', views.notification_preferences, name='notification_preferences'),
    
    # Session management
    path('sessions/', views.active_sessions, name='active_sessions'),
    path('sessions/end/<uuid:uuid>/', views.end_session, name='end_session'),
]