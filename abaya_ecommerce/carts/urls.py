# carts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Cart URLs
    path('', views.cart_detail, name='cart_detail'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('update/', views.update_cart, name='update_cart'),
    path('remove/', views.remove_from_cart, name='remove_from_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    
    # Wishlist URLs
    path('wishlist/', views.wishlist_detail, name='wishlist_detail'),
    path('wishlist/add/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/move-to-cart/', views.move_to_cart, name='move_to_cart'),
]