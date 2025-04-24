# payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Payment methods management
    path('methods/', views.payment_methods, name='payment_methods'),
    path('methods/add/', views.add_payment_method, name='add_payment_method'),
    path('methods/edit/<uuid:uuid>/', views.edit_payment_method, name='edit_payment_method'),
    path('methods/delete/<uuid:uuid>/', views.delete_payment_method, name='delete_payment_method'),
    path('methods/default/<uuid:uuid>/', views.set_default_payment_method, name='set_default_payment_method'),
    
    # Payment processing
    path('process/<str:order_number>/', views.process_payment, name='process_payment'),
    path('options/<str:order_number>/', views.payment_options, name='payment_options'),
    path('success/<str:order_number>/', views.payment_success, name='payment_success'),
    path('cancel/<str:order_number>/', views.payment_cancel, name='payment_cancel'),
    path('webhook/<str:gateway>/', views.payment_webhook, name='payment_webhook'),
    
    # Refunds
    path('refund/<str:order_number>/', views.refund_request, name='refund_request'),
    
    # Transaction history
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('transactions/<uuid:uuid>/', views.transaction_detail, name='transaction_detail'),
]