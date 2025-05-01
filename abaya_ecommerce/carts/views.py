# carts/views.py
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction

from .models import Cart, CartItem, Wishlist, WishlistItem, GuestCart, GuestCartItem
from products.models import Product, Currency, Size, Color, Fabric, FabricColor

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
                # Try to find existing cart item with same variant
                cart_item = CartItem.objects.get(
                    cart=user_cart, 
                    product=guest_item.product,
                    size=guest_item.size,
                    color=guest_item.color,
                    fabric=guest_item.fabric
                )
                # Update quantity
                cart_item.quantity += guest_item.quantity
                cart_item.save()
            except CartItem.DoesNotExist:
                # Create new cart item
                CartItem.objects.create(
                    cart=user_cart,
                    product=guest_item.product,
                    size=guest_item.size,
                    color=guest_item.color,
                    fabric=guest_item.fabric,
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
    
    # Get trending products for recommendations (if available)
    try:
        from products.models import Product
        trending_products = Product.objects.filter(is_active=True).order_by('-views')[:8]
        for product in trending_products:
            product.default_image = product.get_default_image()
    except:
        trending_products = []
    
    return render(request, 'carts/cart_detail.html', {
        'cart': cart,
        'trending_products': trending_products
    })

@require_POST
def add_to_cart(request):
    """Add a product to cart."""
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    
    # Get size, color, and fabric selections
    size_id = request.POST.get('size_id')
    color_id = request.POST.get('color_id')
    fabric_id = request.POST.get('fabric_id')
    
    if quantity <= 0:
        return JsonResponse({
            'status': 'error',
            'message': 'Quantity must be at least 1'
        }, status=400)
    
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Get size, color, and fabric objects if IDs provided
    size = get_object_or_404(Size, id=size_id) if size_id else None
    color = get_object_or_404(Color, id=color_id) if color_id else None
    fabric = get_object_or_404(Fabric, id=fabric_id) if fabric_id else None
    
    # Validate that the selected color is available for the selected fabric
    if color and fabric:
        if not FabricColor.objects.filter(fabric=fabric, color=color).exists():
            return JsonResponse({
                'status': 'error',
                'message': f'Color {color.name} is not available for {fabric.name}'
            }, status=400)
    
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        try:
            # Try to find existing cart item with same variant
            cart_item = CartItem.objects.get(
                cart=cart,
                product=product,
                size=size,
                color=color,
                fabric=fabric
            )
            # Update quantity
            cart_item.quantity += quantity
            cart_item.save()
        except CartItem.DoesNotExist:
            # Create new cart item
            CartItem.objects.create(
                cart=cart,
                product=product,
                size=size,
                color=color,
                fabric=fabric,
                quantity=quantity
            )
    else:
        cart = get_or_create_guest_cart(request)
        
        try:
            # Try to find existing cart item with same variant
            cart_item = GuestCartItem.objects.get(
                cart=cart,
                product=product,
                size=size,
                color=color,
                fabric=fabric
            )
            # Update quantity
            cart_item.quantity += quantity
            cart_item.save()
        except GuestCartItem.DoesNotExist:
            # Create new cart item
            GuestCartItem.objects.create(
                cart=cart,
                product=product,
                size=size,
                color=color,
                fabric=fabric,
                quantity=quantity
            )
    
    # Create variant display string
    variant_parts = []
    if size:
        variant_parts.append(f"Size: {size.name}")
    if color:
        variant_parts.append(f"Color: {color.name}")
    if fabric:
        variant_parts.append(f"Fabric: {fabric.name}")
        
    variant_display = f" ({', '.join(variant_parts)})" if variant_parts else ""
    
    return JsonResponse({
        'status': 'success',
        'message': f"{product.name}{variant_display} added to your cart",
        'cart_count': cart.get_item_count()
    })

@require_POST
def update_cart(request):
    """Update item quantity in cart with improved error handling."""
    try:
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity <= 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Quantity must be at least 1'
            }, status=400)
        
        # Get cart item based on authentication status
        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            cart = cart_item.cart
        else:
            cart = get_or_create_guest_cart(request)
            cart_item = get_object_or_404(GuestCartItem, id=item_id, cart=cart)
        
        # Don't update if quantity hasn't changed
        old_quantity = cart_item.quantity
        if old_quantity == quantity:
            return JsonResponse({
                'status': 'info',
                'message': 'Quantity unchanged',
                'cart_count': cart.get_item_count(),
                'item_total': float(cart_item.get_total_price()),
                'cart_total': float(cart.get_total_price())
            })
        
        # Update quantity and save
        cart_item.quantity = quantity
        cart_item.save()
        
        # Create response data
        response_data = {
            'status': 'success',
            'message': 'Cart updated successfully',
            'cart_count': cart.get_item_count(),
            'item_total': float(cart_item.get_total_price()),
            'cart_total': float(cart.get_total_price())
        }
        
        # Try to add formatted price displays if methods exist
        try:
            if hasattr(cart_item, 'get_total_price_display'):
                response_data['item_total_formatted'] = cart_item.get_total_price_display()
            
            if hasattr(cart, 'get_subtotal_display'):
                response_data['cart_subtotal_formatted'] = cart.get_subtotal_display()
            
            if hasattr(cart, 'get_total_display'):
                response_data['cart_total_formatted'] = cart.get_total_display()
        except Exception as price_error:
            # If formatting fails, log it but continue anyway
            import logging
            logging.error(f"Error formatting prices: {price_error}")
        
        return JsonResponse(response_data)
    
    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Invalid quantity: {str(e)}'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'status': 'error',
            'message': f'An unexpected error occurred: {str(e)}'
        }, status=500)
    
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
    variant_display = cart_item.get_variant_display()
    if variant_display:
        product_name = f"{product_name} ({variant_display})"
        
    cart = cart_item.cart
    cart_item.delete()
    
    # Get formatted total if available
    try:
        cart_total_formatted = cart.get_total_display()
    except:
        cart_total_formatted = None
    
    response_data = {
        'status': 'success',
        'message': f"{product_name} removed from your cart",
        'cart_count': cart.get_item_count(),
        'cart_total': float(cart.get_total_price())
    }
    
    if cart_total_formatted:
        response_data['cart_total_formatted'] = cart_total_formatted
    
    return JsonResponse(response_data)

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
    
    # Add default images to wishlist items
    for item in wishlist.items.all():
        item.product.default_image = item.product.get_default_image()
        
    return render(request, 'carts/wishlist_detail.html', {'wishlist': wishlist})

@login_required
@require_POST
def add_to_wishlist(request):
    """Add a product to wishlist."""
    product_id = request.POST.get('product_id')
    
    # Get size, color, and fabric selections (optional for wishlist)
    size_id = request.POST.get('size_id')
    color_id = request.POST.get('color_id')
    fabric_id = request.POST.get('fabric_id')
    
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Get size, color, and fabric objects if IDs provided
    size = get_object_or_404(Size, id=size_id) if size_id else None
    color = get_object_or_404(Color, id=color_id) if color_id else None
    fabric = get_object_or_404(Fabric, id=fabric_id) if fabric_id else None
    
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    
    # Check if product with same variant already in wishlist
    if WishlistItem.objects.filter(wishlist=wishlist, product=product, size=size, color=color, fabric=fabric).exists():
        return JsonResponse({
            'status': 'info',
            'message': 'This product is already in your wishlist'
        })
    
    # Add to wishlist
    WishlistItem.objects.create(
        wishlist=wishlist,
        product=product,
        size=size,
        color=color,
        fabric=fabric
    )
    
    # Create variant display string
    variant_parts = []
    if size:
        variant_parts.append(f"Size: {size.name}")
    if color:
        variant_parts.append(f"Color: {color.name}")
    if fabric:
        variant_parts.append(f"Fabric: {fabric.name}")
        
    variant_display = f" ({', '.join(variant_parts)})" if variant_parts else ""
    
    return JsonResponse({
        'status': 'success',
        'message': f"{product.name}{variant_display} added to your wishlist",
        'wishlist_count': wishlist.get_item_count()
    })

@login_required
@require_POST
def remove_from_wishlist(request):
    """Remove an item from wishlist."""
    item_id = request.POST.get('item_id')
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    
    product_name = wishlist_item.product.name
    variant_display = wishlist_item.get_variant_display()
    if variant_display:
        product_name = f"{product_name} ({variant_display})"
        
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
        # Try to find existing cart item with same variant
        cart_item = CartItem.objects.get(
            cart=cart, 
            product=wishlist_item.product,
            size=wishlist_item.size,
            color=wishlist_item.color,
            fabric=wishlist_item.fabric
        )
        # Update quantity
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        # Create new cart item
        CartItem.objects.create(
            cart=cart,
            product=wishlist_item.product,
            size=wishlist_item.size,
            color=wishlist_item.color,
            fabric=wishlist_item.fabric,
            quantity=1
        )
    
    # Remove from wishlist
    product_name = wishlist_item.product.name
    variant_display = wishlist_item.get_variant_display()
    if variant_display:
        product_name = f"{product_name} ({variant_display})"
        
    wishlist = wishlist_item.wishlist
    wishlist_item.delete()
    
    return JsonResponse({
        'status': 'success',
        'message': f"{product_name} moved to your cart",
        'cart_count': cart.get_item_count(),
        'wishlist_count': wishlist.get_item_count()
    })

@login_required
@require_POST
def add_all_to_cart(request):
    """Add all wishlist items to cart."""
    wishlist = get_object_or_404(Wishlist, user=request.user)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    if not wishlist.items.exists():
        return JsonResponse({
            'status': 'info',
            'message': 'Your wishlist is empty'
        })
    
    count = 0
    for wishlist_item in wishlist.items.all():
        try:
            # Try to find existing cart item with same variant
            cart_item = CartItem.objects.get(
                cart=cart, 
                product=wishlist_item.product,
                size=wishlist_item.size,
                color=wishlist_item.color,
                fabric=wishlist_item.fabric
            )
            # Update quantity
            cart_item.quantity += 1
            cart_item.save()
        except CartItem.DoesNotExist:
            # Create new cart item
            CartItem.objects.create(
                cart=cart,
                product=wishlist_item.product,
                size=wishlist_item.size,
                color=wishlist_item.color,
                fabric=wishlist_item.fabric,
                quantity=1
            )
        count += 1
    
    if count > 0:
        messages.success(request, f"{count} items added to your cart")
    else:
        messages.info(request, "No items were added to your cart")
    
    return redirect('cart_detail')

@login_required
@require_POST
def clear_wishlist(request):
    """Clear all items from wishlist."""
    wishlist = get_object_or_404(Wishlist, user=request.user)
    wishlist.items.all().delete()
    
    messages.success(request, "Your wishlist has been cleared")
    return redirect('wishlist_detail')