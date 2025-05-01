# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard Home
    path('', views.dashboard_home, name='home'),
    
    # Category Management
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<uuid:uuid>/edit/', views.category_edit, name='category_edit'),
    path('categories/<uuid:uuid>/delete/', views.category_delete, name='category_delete'),
    
    # Product Management
     path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<uuid:uuid>/', views.product_detail, name='product_detail'),
    path('products/<uuid:uuid>/edit/', views.product_edit, name='product_edit'),
    path('products/<uuid:uuid>/delete/', views.product_delete, name='product_delete'),
    path('products/<uuid:uuid>/media/', views.product_media, name='product_media'),
    path('products/<uuid:uuid>/media/add/', views.product_media_add, name='product_media_add'),
    path('products/<uuid:uuid>/media/<uuid:media_id>/edit/', views.product_media_edit, name='product_media_edit'),
    path('products/<uuid:uuid>/media/<uuid:media_id>/delete/', views.product_media_delete, name='product_media_delete'),
    
    # Attribute Management
    path('attributes/sizes/', views.size_list, name='size_list'),
    path('attributes/sizes/create/', views.size_create, name='size_create'),
    path('attributes/sizes/<uuid:uuid>/edit/', views.size_edit, name='size_edit'),
    path('attributes/sizes/<uuid:uuid>/delete/', views.size_delete, name='size_delete'),
    
    path('attributes/fabrics/', views.fabric_list, name='fabric_list'),
    path('attributes/fabrics/create/', views.fabric_create, name='fabric_create'),
    path('attributes/fabrics/<uuid:uuid>/edit/', views.fabric_edit, name='fabric_edit'),
    path('attributes/fabrics/<uuid:uuid>/delete/', views.fabric_delete, name='fabric_delete'),
    
    path('attributes/colors/', views.color_list, name='color_list'),
    path('attributes/colors/create/', views.color_create, name='color_create'),
    path('attributes/colors/<uuid:uuid>/edit/', views.color_edit, name='color_edit'),
    path('attributes/colors/<uuid:uuid>/delete/', views.color_delete, name='color_delete'),
    
    # Currency Management
    path('currencies/', views.currency_list, name='currency_list'),
    path('currencies/create/', views.currency_create, name='currency_create'),
    path('currencies/<uuid:uuid>/edit/', views.currency_edit, name='currency_edit'),
    path('currencies/<uuid:uuid>/delete/', views.currency_delete, name='currency_delete'),
    
    # Order Management
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/update-status/', views.order_update_status, name='order_update_status'),
    
    # Coupon Management
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.coupon_create, name='coupon_create'),
    path('coupons/<uuid:uuid>/edit/', views.coupon_edit, name='coupon_edit'),
    path('coupons/<uuid:uuid>/delete/', views.coupon_delete, name='coupon_delete'),
    
    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/<uuid:uuid>/', views.user_detail, name='user_detail'),
    path('users/<uuid:uuid>/orders/', views.user_orders, name='user_orders'),
    
    # Reports
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/products/', views.product_report, name='product_report'),
    path('reports/customers/', views.customer_report, name='customer_report'),
    
    # Activity Logs
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    
    # Settings
    path('settings/', views.dashboard_settings, name='settings'),
]