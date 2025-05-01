# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Product pages
    path('', views.product_list, name='product_list'),
        # Search
    path('search/', views.search, name='search'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),
    path('<slug:slug>/review/', views.add_review, name='add_review'),
    
    # Category pages
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    
    # Static pages
    # path('page/<slug:slug>/', views.page_detail, name='page_detail'),
    

    
    # API endpoints
    path('api/search/', views.product_search_api, name='product_search_api'),
    path('api/product/<uuid:product_id>/attributes/', views.get_product_attributes_api, name='get_product_attributes_api'),
    path('api/fabric/<uuid:fabric_id>/colors/', views.get_colors_for_fabric, name='get_colors_for_fabric'),
]