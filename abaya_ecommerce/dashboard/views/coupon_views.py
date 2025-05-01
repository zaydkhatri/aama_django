# dashboard/views/coupon_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from orders.models import Coupon, CouponCategory, CouponProduct
from products.models import Category, Product
from dashboard.forms import CouponForm
from dashboard.utils import staff_member_required, log_admin_activity, paginate_queryset

@staff_member_required
def coupon_list(request):
    """Display a list of coupons."""
    # Get all coupons
    coupons = Coupon.objects.all().order_by('-created_at')
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        coupons = coupons.filter(
            Q(code__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Status filter
    status = request.GET.get('status')
    if status == 'active':
        coupons = coupons.filter(is_active=True)
    elif status == 'inactive':
        coupons = coupons.filter(is_active=False)
    
    # Expiry filter
    expiry = request.GET.get('expiry')
    now = timezone.now()
    if expiry == 'expired':
        coupons = coupons.filter(end_date__lt=now)
    elif expiry == 'valid':
        coupons = coupons.filter(end_date__gte=now)
    
    # Paginate results
    coupons = paginate_queryset(request, coupons, 20)
    
    return render(request, 'dashboard/coupons/list.html', {
        'coupons': coupons,
        'search_query': search_query,
        'status': status,
        'expiry': expiry,
    })

@staff_member_required
def coupon_create(request):
    """Create a new coupon."""
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save()
            
            # Handle category and product restrictions if provided
            categories = request.POST.getlist('categories')
            products = request.POST.getlist('products')
            
            for category_id in categories:
                try:
                    CouponCategory.objects.create(
                        coupon=coupon,
                        category_id=category_id
                    )
                except Exception:
                    pass
            
            for product_id in products:
                try:
                    CouponProduct.objects.create(
                        coupon=coupon,
                        product_id=product_id
                    )
                except Exception:
                    pass
            
            # Log activity
            log_admin_activity(
                request.user,
                'CREATE',
                'Coupon',
                coupon.id,
                f"Created coupon '{coupon.code}'",
                request
            )
            
            messages.success(request, f"Coupon '{coupon.code}' has been created successfully.")
            return redirect('dashboard:coupon_list')
    else:
        form = CouponForm()
    
    # Get categories and popular products for selection
    categories = Category.objects.filter(is_active=True)
    popular_products = Product.objects.filter(is_active=True).order_by('-views')[:20]
    
    return render(request, 'dashboard/coupons/form.html', {
        'form': form,
        'categories': categories,
        'popular_products': popular_products,
        'title': 'Create Coupon',
    })

@staff_member_required
def coupon_edit(request, uuid):
    """Edit an existing coupon."""
    coupon = get_object_or_404(Coupon, id=uuid)
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            coupon = form.save()
            
            # Handle category and product restrictions
            # First, clear existing associations
            CouponCategory.objects.filter(coupon=coupon).delete()
            CouponProduct.objects.filter(coupon=coupon).delete()
            
            # Then create new ones
            categories = request.POST.getlist('categories')
            products = request.POST.getlist('products')
            
            for category_id in categories:
                try:
                    CouponCategory.objects.create(
                        coupon=coupon,
                        category_id=category_id
                    )
                except Exception:
                    pass
            
            for product_id in products:
                try:
                    CouponProduct.objects.create(
                        coupon=coupon,
                        product_id=product_id
                    )
                except Exception:
                    pass
            
            # Log activity
            log_admin_activity(
                request.user,
                'UPDATE',
                'Coupon',
                coupon.id,
                f"Updated coupon '{coupon.code}'",
                request
            )
            
            messages.success(request, f"Coupon '{coupon.code}' has been updated successfully.")
            return redirect('dashboard:coupon_list')
    else:
        form = CouponForm(instance=coupon)
    
    # Get categories and popular products for selection
    categories = Category.objects.filter(is_active=True)
    popular_products = Product.objects.filter(is_active=True).order_by('-views')[:20]
    
    # Get current selections
    selected_categories = CouponCategory.objects.filter(coupon=coupon).values_list('category_id', flat=True)
    selected_products = CouponProduct.objects.filter(coupon=coupon).values_list('product_id', flat=True)
    
    return render(request, 'dashboard/coupons/form.html', {
        'form': form,
        'coupon': coupon,
        'categories': categories,
        'popular_products': popular_products,
        'selected_categories': list(selected_categories),
        'selected_products': list(selected_products),
        'title': f"Edit Coupon: {coupon.code}",
    })

@staff_member_required
def coupon_delete(request, uuid):
    """Delete a coupon."""
    coupon = get_object_or_404(Coupon, id=uuid)
    
    if request.method == 'POST':
        # Get coupon details for logging before deletion
        coupon_code = coupon.code
        coupon_id = str(coupon.id)
        
        # Delete the coupon
        coupon.delete()
        
        # Log activity
        log_admin_activity(
            request.user,
            'DELETE',
            'Coupon',
            coupon_id,
            f"Deleted coupon '{coupon_code}'",
            request
        )
        
        messages.success(request, f"Coupon '{coupon_code}' has been deleted successfully.")
        return redirect('dashboard:coupon_list')
    
    return render(request, 'dashboard/coupons/delete.html', {
        'coupon': coupon,
    })