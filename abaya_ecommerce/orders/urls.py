# orders/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Checkout process
    path('checkout/', views.checkout, name='checkout'),
    path('apply-coupon/', views.apply_coupon_view, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    
    # Payment process
    path('payment/<str:order_number>/', views.order_payment, name='order_payment'),
    path('process-payment/<str:order_number>/', views.process_payment, name='process_payment'),
    path('success/<str:order_number>/', views.order_success, name='order_success'),
    
    # Order management
    path('history/', views.order_history, name='order_history'),
    path('detail/<str:order_number>/', views.order_detail, name='order_detail'),
    path('invoice/<str:order_number>/', views.order_invoice, name='order_invoice'),
    path('tracking/<str:order_number>/', views.order_tracking, name='order_tracking'),
    path('cancel/<str:order_number>/', views.order_cancel, name='order_cancel'),
    
    # Return management
    path('request-return/<str:order_number>/', views.request_return, name='request_return'),
    path('return/<str:return_number>/', views.return_detail, name='return_detail'),
    path('returns/', views.return_history, name='return_history'),
]