from django.urls import path
from dashboard.views import (
    dashboard_views,
    category_views,
    product_views,
    order_views,
    user_views,
    report_views
)

app_name = 'dashboard'

urlpatterns = [
    # Authentication
    path('login/', dashboard_views.dashboard_login, name='login'),
    path('logout/', dashboard_views.dashboard_logout, name='logout'),
    
    # Dashboard
    path('', dashboard_views.dashboard_home, name='home'),
    path('profile/', dashboard_views.admin_profile, name='profile'),
    path('settings/', dashboard_views.dashboard_settings, name='settings'),
    path('activities/', dashboard_views.activity_log, name='activities'),
    
    # Categories
    path('categories/', category_views.category_list, name='category_list'),
    path('categories/create/', category_views.category_create, name='category_create'),
    path('categories/edit/<uuid:pk>/', category_views.category_edit, name='category_edit'),
    path('categories/delete/<uuid:pk>/', category_views.category_delete, name='category_delete'),
    
    # Products
    path('products/', product_views.product_list, name='product_list'),
    path('products/create/', product_views.product_create, name='product_create'),
    path('products/edit/<uuid:pk>/', product_views.product_edit, name='product_edit'),
    path('products/delete/<uuid:pk>/', product_views.product_delete, name='product_delete'),
    path('products/images/<uuid:pk>/', product_views.product_images, name='product_images'),
    path('products/variants/<uuid:pk>/', product_views.product_variants, name='product_variants'),
    
    # Product Attributes
    path('sizes/', product_views.size_list, name='size_list'),
    path('sizes/create/', product_views.size_create, name='size_create'),
    path('sizes/edit/<uuid:pk>/', product_views.size_edit, name='size_edit'),
    path('sizes/delete/<uuid:pk>/', product_views.size_delete, name='size_delete'),
    
    path('colors/', product_views.color_list, name='color_list'),
    path('colors/create/', product_views.color_create, name='color_create'),
    path('colors/edit/<uuid:pk>/', product_views.color_edit, name='color_edit'),
    path('colors/delete/<uuid:pk>/', product_views.color_delete, name='color_delete'),
    
    path('fabrics/', product_views.fabric_list, name='fabric_list'),
    path('fabrics/create/', product_views.fabric_create, name='fabric_create'),
    path('fabrics/edit/<uuid:pk>/', product_views.fabric_edit, name='fabric_edit'),
    path('fabrics/delete/<uuid:pk>/', product_views.fabric_delete, name='fabric_delete'),
    
    # Orders
    path('orders/', order_views.order_list, name='order_list'),
    path('orders/detail/<uuid:pk>/', order_views.order_detail, name='order_detail'),
    path('orders/edit/<uuid:pk>/', order_views.order_edit, name='order_edit'),
    path('orders/invoice/<uuid:pk>/', order_views.order_invoice, name='order_invoice'),
    path('orders/status/<uuid:pk>/', order_views.update_order_status, name='update_order_status'),
    
    # Returns
    path('returns/', order_views.return_list, name='return_list'),
    path('returns/detail/<uuid:pk>/', order_views.return_detail, name='return_detail'),
    path('returns/update/<uuid:pk>/', order_views.update_return_status, name='update_return_status'),
    
    # Users
    path('users/', user_views.user_list, name='user_list'),
    path('users/create/', user_views.user_create, name='user_create'),
    path('users/detail/<uuid:pk>/', user_views.user_detail, name='user_detail'),
    path('users/edit/<uuid:pk>/', user_views.user_edit, name='user_edit'),
    
    # Reports
    path('reports/sales/', report_views.sales_report, name='sales_report'),
    path('reports/products/', report_views.product_report, name='product_report'),
    path('reports/customers/', report_views.customer_report, name='customer_report'),
    path('reports/export/sales/', report_views.export_sales_report, name='export_sales_report'),
    path('reports/export/products/', report_views.export_product_report, name='export_product_report'),
    path('reports/export/customers/', report_views.export_customer_report, name='export_customer_report'),
    
    # AJAX endpoints
    path('api/orders/chart/', report_views.orders_chart_data, name='orders_chart_data'),
    path('api/sales/chart/', report_views.sales_chart_data, name='sales_chart_data'),
    path('api/products/chart/', report_views.products_chart_data, name='products_chart_data'),
]