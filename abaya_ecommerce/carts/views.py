from django.shortcuts import render

# Create your views here.
# carts/views.py
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction

from .models import Cart, CartItem, Wishlist, WishlistItem, GuestCart, GuestCartItem
from products.models import Product, Currency

def get_or_create_guest_cart(request):
    """Get or create a guest cart based on session key."""
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    
    cart, created = GuestCart.objects.get_or_create(session_key=session_key)
    return cart

def merge_carts(user_cart, guest_cart):
    """Merge a guest cart into a user cart when user logs in."""
    with transaction.atomic():
        for guest_item in guest_cart.items.all():
            try:
                # Try to find existing cart item
                cart_item = CartItem.objects.get(cart=user_cart, product=guest_item.product)
                # Update quantity
                cart_item.quantity += guest_item.quantity
                cart_item.save()
            except CartItem.DoesNotExist:
                # Create new cart item
                CartItem.objects.create(
                    cart=user_cart,
                    product=guest_item.product,
                    quantity=guest_item.quantity
                )
        
        # Clear guest cart
        guest_cart.clear()

def cart_detail(request):
    """Display the shopping cart."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if there's a guest cart to merge
        if request.session.session_key:
            try:
                guest_cart = GuestCart.objects.get(session_key=request.session.session_key)
                if guest_cart.items.exists():
                    merge_carts(cart, guest_cart)
                    messages.info(request, "We've added the items from your guest cart to your account.")
            except GuestCart.DoesNotExist:
                pass
    else:
        cart = get_or_create_guest_cart(request)
    
    # Add default images to cart items
    for item in cart.items.all():
        item.product.default_image = item.product.get_default_image()
    
    return render(request, 'carts/cart_detail.html', {'cart': cart})

@require_POST
def add_to_cart(request):
    """Add a product to cart."""
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        return JsonResponse({
            'status': 'error',
            'message': 'Quantity must be at least 1'
        }, status=400)
    
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Check stock
    if product.quantity < quantity:
        return JsonResponse({
            'status': 'error',
            'message': f'Sorry, we only have {product.quantity} in stock'
        }, status=400)
    
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        try:
            # Try to find existing cart item
            cart_item = CartItem.objects.get(cart=cart, product=product)
            # Update quantity
            cart_item.quantity += quantity
            cart_item.save()
        except CartItem.DoesNotExist:
            # Create new cart item
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity
            )
    else:
        cart = get_or_create_guest_cart(request)
        
        try:
            # Try to find existing cart item
            cart_item = GuestCartItem.objects.get(cart=cart, product=product)
            # Update quantity
            cart_item.quantity += quantity
            cart_item.save()
        except GuestCartItem.DoesNotExist:
            # Create new cart item
            GuestCartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity
            )
    
    return JsonResponse({
        'status': 'success',
        'message': f"{product.name} added to your cart",
        'cart_count': cart.get_item_count()
    })

@require_POST
def update_cart(request):
    """Update item quantity in cart."""
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        return JsonResponse({
            'status': 'error',
            'message': 'Quantity must be at least 1'
        }, status=400)
    
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        cart = get_or_create_guest_cart(request)
        cart_item = get_object_or_404(GuestCartItem, id=item_id, cart=cart)
    
    # Check stock
    if cart_item.product.quantity < quantity:
        return JsonResponse({
            'status': 'error',
            'message': f'Sorry, we only have {cart_item.product.quantity} in stock'
        }, status=400)
    
    cart_item.quantity = quantity
    cart_item.save()
    
    cart = cart_item.cart
    
    return JsonResponse({
        'status': 'success',
        'message': 'Cart updated',
        'cart_count': cart.get_item_count(),
        'item_total': float(cart_item.get_total_price()),
        'cart_total': float(cart.get_total_price())
    })

@require_POST
def remove_from_cart(request):
    """Remove an item from cart."""
    item_id = request.POST.get('item_id')
    
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        cart = get_or_create_guest_cart(request)
        cart_item = get_object_or_404(GuestCartItem, id=item_id, cart=cart)
    
    product_name = cart_item.product.name
    cart = cart_item.cart
    cart_item.delete()
    
    return JsonResponse({
        'status': 'success',
        'message': f"{product_name} removed from your cart",
        'cart_count': cart.get_item_count(),
        'cart_total': float(cart.get_total_price())
    })

@require_POST
def clear_cart(request):
    """Clear all items from cart."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        cart = get_or_create_guest_cart(request)
    
    cart.clear()
    
    return JsonResponse({
        'status': 'success',
        'message': "Your cart has been cleared",
        'cart_count': 0,
        'cart_total': 0.0
    })

@login_required
def wishlist_detail(request):
    """Display the wishlist."""
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'carts/wishlist_detail.html', {'wishlist': wishlist})

@login_required
@require_POST
def add_to_wishlist(request):
    """Add a product to wishlist."""
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    
    # Check if product already in wishlist
    if WishlistItem.objects.filter(wishlist=wishlist, product=product).exists():
        return JsonResponse({
            'status': 'info',
            'message': 'This product is already in your wishlist'
        })
    
    # Add to wishlist
    WishlistItem.objects.create(
        wishlist=wishlist,
        product=product
    )
    
    return JsonResponse({
        'status': 'success',
        'message': f"{product.name} added to your wishlist",
        'wishlist_count': wishlist.get_item_count()
    })

@login_required
@require_POST
def remove_from_wishlist(request):
    """Remove an item from wishlist."""
    item_id = request.POST.get('item_id')
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    
    product_name = wishlist_item.product.name
    wishlist = wishlist_item.wishlist
    wishlist_item.delete()
    
    return JsonResponse({
        'status': 'success',
        'message': f"{product_name} removed from your wishlist",
        'wishlist_count': wishlist.get_item_count()
    })

@login_required
@require_POST
def move_to_cart(request):
    """Move an item from wishlist to cart."""
    item_id = request.POST.get('item_id')
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    try:
        # Try to find existing cart item
        cart_item = CartItem.objects.get(cart=cart, product=wishlist_item.product)
        # Update quantity
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        # Create new cart item
        CartItem.objects.create(
            cart=cart,
            product=wishlist_item.product,
            quantity=1
        )
    
    # Remove from wishlist
    product_name = wishlist_item.product.name
    wishlist = wishlist_item.wishlist
    wishlist_item.delete()
    
    return JsonResponse({
        'status': 'success',
        'message': f"{product_name} moved to your cart",
        'cart_count': cart.get_item_count(),
        'wishlist_count': wishlist.get_item_count()
    })