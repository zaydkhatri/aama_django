# products/views.py
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Avg, Count
from django.utils import timezone

from .models import (
    Category, Product, Currency, Review, ProductView, 
    SearchQuery, ReviewImage, Size, Color, Fabric,
    FabricColor, ProductFabric, ProductSize
)
from .forms import ReviewForm, ProductFilterForm, ProductVariantForm

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_session_id(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key

def home(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    top_categories = Category.objects.filter(is_active=True)[:6]
    
    # Add default images to products
    for product in featured_products:
        product.default_image = product.get_default_image()
    
    for product in new_arrivals:
        product.default_image = product.get_default_image()
    
    return render(request, 'products/home.html', {
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'top_categories': top_categories,
    })

def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    sizes = Size.objects.filter(is_active=True)
    fabrics = Fabric.objects.filter(is_active=True)
    colors = Color.objects.filter(is_active=True)
    
    # Filtering
    form = ProductFilterForm(request.GET)
    if form.is_valid():
        # Category filter
        category_id = form.cleaned_data.get('category')
        if category_id:
            category = get_object_or_404(Category, id=category_id)
            products = category.get_all_products()
        
        # Price range filter
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)
        
        # Size filter
        size = form.cleaned_data.get('size')
        if size:
            products = products.filter(sizes=size)
        
        # Fabric filter
        fabric = form.cleaned_data.get('fabric')
        if fabric:
            products = products.filter(fabrics=fabric)
        
        # Color filter
        color = form.cleaned_data.get('color')
        if color:
            # Get products that have this color available via their fabrics
            fabric_ids = FabricColor.objects.filter(color=color).values_list('fabric_id', flat=True)
            products = products.filter(product_fabrics__fabric_id__in=fabric_ids).distinct()
        
        # Sort options
        sort_option = request.GET.get('sort') or form.cleaned_data.get('sort')
        if sort_option == 'price_low':
            products = products.order_by('price')
        elif sort_option == 'price_high':
            products = products.order_by('-price')
        elif sort_option == 'newest':
            products = products.order_by('-created_at')
        elif sort_option == 'rating':
            products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
        elif sort_option == 'popularity':
            products = products.annotate(view_count=Count('views')).order_by('-view_count')
    
    # Search
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(sku__icontains=query) |
            Q(categories__name__icontains=query)
        ).distinct()
        
        # Log search query
        SearchQuery.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            session_id=get_session_id(request),
            results_count=products.count()
        )
    
    # IMPORTANT: Add default images to all products AFTER all filtering and sorting
    for product in products:
        product.default_image = product.get_default_image()
    
    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Get any query parameters for passing to pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    
    return render(request, 'products/product_list.html', {
        'products': products,
        'categories': categories,
        'sizes': sizes,
        'fabrics': fabrics,
        'colors': colors,
        'form': form,
        'query': query,
        'query_params': query_params.urlencode(),
        'current_sorting': request.GET.get('sort', '')
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    related_products = Product.objects.filter(
        categories__in=product.categories.all()
    ).exclude(id=product.id).distinct()[:4]
    
    # Process related products to add default images
    for related_product in related_products:
        related_product.default_image = related_product.get_default_image()
    
    # Set the default image properly using the model's method
    product.default_image = product.get_default_image()
    
    # Get all product images for gallery
    product.all_images = product.media.filter(type='IMAGE').order_by('sort_order')
    
    # Get available sizes for this product
    sizes = Size.objects.filter(
        is_active=True,
        products=product
    ).order_by('sort_order')
    
    # Get available fabrics for this product
    fabrics = Fabric.objects.filter(
        is_active=True,
        products=product
    )
    
    # Create a dictionary of colors available for each fabric
    fabric_colors = {}
    for fabric in fabrics:
        fabric_colors[str(fabric.id)] = list(Color.objects.filter(
            is_active=True,
            fabrics=fabric
        ).values('id', 'name', 'color_code'))
    
    # Get variant selection form
    variant_form = ProductVariantForm(product=product)
    
    # Get reviews
    reviews = product.reviews.filter(is_published=True).select_related('user').prefetch_related('images')
    
    # Get review statistics
    review_stats = {
        'avg_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
        'count': reviews.count(),
        'rating_5': reviews.filter(rating=5).count(),
        'rating_4': reviews.filter(rating=4).count(),
        'rating_3': reviews.filter(rating=3).count(),
        'rating_2': reviews.filter(rating=2).count(),
        'rating_1': reviews.filter(rating=1).count(),
    }
    
    # Log product view
    ProductView.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        session_id=get_session_id(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        ip_address=get_client_ip(request),
        device_type=request.META.get('HTTP_USER_AGENT', '').lower()
    )
    
    # Review form
    form = ReviewForm()
    
    return render(request, 'products/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'sizes': sizes,
        'fabrics': fabrics,
        'fabric_colors': fabric_colors,
        'variant_form': variant_form,
        'reviews': reviews,
        'review_stats': review_stats,
        'form': form,
    })

def get_colors_for_fabric(request, fabric_id):
    """AJAX endpoint to get colors for a specific fabric"""
    try:
        # Get the fabric by ID
        fabric = get_object_or_404(Fabric, id=fabric_id)
        
        # Find all colors associated with this fabric through the FabricColor model
        fabric_colors = FabricColor.objects.filter(fabric=fabric)
        color_ids = fabric_colors.values_list('color_id', flat=True)
        
        # Get the actual Color objects
        colors = Color.objects.filter(id__in=color_ids, is_active=True)
        
        # Convert to a list of dictionaries for JSON response
        colors_data = list(colors.values('id', 'name', 'color_code'))
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'colors': colors_data
        })
    except Exception as e:
        # Log the error for debugging
        import logging
        logging.error(f"Error in get_colors_for_fabric: {str(e)}")
        
        # Return error response
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products_list = category.get_all_products()
    
    # Set default image for each product
    for product in products_list:
        product.default_image = product.get_default_image()
    
    # Filtering
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort = request.GET.get('sort')
    size_id = request.GET.get('size')
    fabric_id = request.GET.get('fabric')
    color_id = request.GET.get('color')
    
    if min_price:
        products_list = products_list.filter(price__gte=min_price)
    
    if max_price:
        products_list = products_list.filter(price__lte=max_price)
    
    if size_id:
        products_list = products_list.filter(sizes__id=size_id)
    
    if fabric_id:
        products_list = products_list.filter(fabrics__id=fabric_id)
    
    if color_id:
        # Get products that have this color available via their fabrics
        fabric_ids = FabricColor.objects.filter(color_id=color_id).values_list('fabric_id', flat=True)
        products_list = products_list.filter(product_fabrics__fabric_id__in=fabric_ids).distinct()
    
    # Sorting
    if sort:
        if sort == 'price_low':
            products_list = products_list.order_by('price')
        elif sort == 'price_high':
            products_list = products_list.order_by('-price')
        elif sort == 'newest':
            products_list = products_list.order_by('-created_at')
        elif sort == 'popularity':
            products_list = products_list.annotate(view_count=Count('views')).order_by('-view_count')
    
    # Pagination
    paginator = Paginator(products_list, 12)  # Show 12 products per page
    page = request.GET.get('page')
    
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Get all categories for sidebar
    categories = Category.objects.filter(is_active=True)
    
    # Get sizes, fabrics, and colors for filtering
    sizes = Size.objects.filter(is_active=True)
    fabrics = Fabric.objects.filter(is_active=True)
    colors = Color.objects.filter(is_active=True)
    
    return render(request, 'products/category_detail.html', {
        'category': category,
        'products': products,
        'categories': categories,
        'sizes': sizes,
        'fabrics': fabrics,
        'colors': colors,
        'all_products_count': Product.objects.filter(is_active=True).count(),
        'selected_size': size_id,
        'selected_fabric': fabric_id,
        'selected_color': color_id,
    })

@login_required
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            
            # Check if user has purchased this product
            from orders.models import OrderItem
            has_purchased = OrderItem.objects.filter(
                order__user=request.user,
                product=product,
                order__status__in=['DELIVERED', 'COMPLETED']
            ).exists()
            
            review.is_verified = has_purchased
            review.save()
            
            # Handle multiple uploaded files
            if request.FILES:
                for image in request.FILES.getlist('images'):
                    ReviewImage.objects.create(
                        review=review,
                        image=image
                    )
            
            messages.success(request, 'Thank you! Your review has been submitted.')
            return redirect('product_detail', slug=slug)
    
    # If not POST or form invalid
    messages.error(request, 'There was an error submitting your review. Please try again.')
    return redirect('product_detail', slug=slug)

def search(request):
    """Display search results for products."""
    query = request.GET.get('q', '')
    
    if query:
        # Search for products that match the query in name, description, or SKU
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(sku__icontains=query) |
            Q(categories__name__icontains=query)
        ).filter(is_active=True).distinct()
        
        # Add default images to search results
        for product in products:
            product.default_image = product.get_default_image()
        
        # Log search query
        SearchQuery.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            session_id=get_session_id(request),
            results_count=products.count()
        )
    else:
        products = Product.objects.none()
    
    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    return render(request, 'products/search_results.html', {
        'products': products,
        'query': query,
        'count': paginator.count,
    })

# API Endpoints
def product_search_api(request):
    query = request.GET.get('q', '')
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(sku__icontains=query)
    ).values('id', 'name', 'slug', 'price')[:10]
    
    return JsonResponse({'results': list(products)})

def get_product_attributes_api(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        
        # Get sizes
        sizes = Size.objects.filter(
            products=product,
            is_active=True
        ).values('id', 'name')
        
        # Get fabrics
        fabrics = Fabric.objects.filter(
            products=product,
            is_active=True
        ).values('id', 'name')
        
        # Get available colors based on product's fabrics
        fabric_ids = product.fabrics.values_list('id', flat=True)
        colors = Color.objects.filter(
            fabrics__in=fabric_ids,
            is_active=True
        ).distinct().values('id', 'name', 'color_code')
        
        return JsonResponse({
            'product_id': str(product.id),
            'sizes': list(sizes),
            'fabrics': list(fabrics),
            'colors': list(colors)
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)