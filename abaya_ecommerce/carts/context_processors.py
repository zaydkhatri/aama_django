# carts/context_processors.py
from .models import Cart, Wishlist, GuestCart

def cart(request):
    """
    Context processor to make cart data available across all templates.
    """
    cart_count = 0
    cart_total = 0
    wishlist_count = 0
    
    if request.user.is_authenticated:
        # Get user cart
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.get_item_count()
            cart_total = cart.get_total_price()
        except Cart.DoesNotExist:
            cart = None
        
        # Get user wishlist
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_count = wishlist.get_item_count()
        except Wishlist.DoesNotExist:
            wishlist = None
    else:
        # Get guest cart from session
        session_key = request.session.session_key
        if session_key:
            try:
                guest_cart = GuestCart.objects.get(session_key=session_key)
                cart_count = guest_cart.get_item_count()
                cart_total = guest_cart.get_total_price()
            except GuestCart.DoesNotExist:
                pass
    
    return {
        'cart_count': cart_count,
        'cart_total': cart_total,
        'wishlist_count': wishlist_count,
    }