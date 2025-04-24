from django.shortcuts import render

# Create your views here.
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
    Category, Product, Attribute, AttributeValue, ProductAttribute,
    Currency, Review, ProductView, SearchQuery
)
from .forms import ReviewForm, ProductFilterForm

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
    
    return render(request, 'products/home.html', {
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'top_categories': top_categories,
    })

def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    attributes = Attribute.objects.filter(is_active=True)
    
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
        
        # Attribute filters
        for attr in attributes:
            attr_values = request.GET.getlist(f'attribute_{attr.id}')
            if attr_values:
                products = products.filter(
                    attributes__attribute=attr,
                    attributes__attribute_value__id__in=attr_values
                ).distinct()
        
        # Sort options
        sort_option = form.cleaned_data.get('sort')
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
    
    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    return render(request, 'products/product_list.html', {
        'products': products,
        'categories': categories,
        'attributes': attributes,
        'form': form,
        'query': query,
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related_products = Product.objects.filter(
        categories__in=product.categories.all()
    ).exclude(id=product.id).distinct()[:4]
    
    # Get all attributes and their values for this product
    product_attributes = product.attributes.all().select_related('attribute', 'attribute_value')
    
    # Group attributes by attribute name
    grouped_attributes = {}
    for pa in product_attributes:
        attr_name = pa.attribute.name
        if attr_name not in grouped_attributes:
            grouped_attributes[attr_name] = []
        grouped_attributes[attr_name].append(pa.attribute_value)
    
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
        'grouped_attributes': grouped_attributes,
        'reviews': reviews,
        'review_stats': review_stats,
        'form': form,
    })

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = category.get_all_products()
    
    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    return render(request, 'products/category_detail.html', {
        'category': category,
        'products': products,
    })

@login_required
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
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
            
            # Save review images
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

def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, 'products/page_detail.html', {'page': page})

def search(request):
    query = request.GET.get('q', '')
    
    if query:
        products = Product.objects.filter(
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
        attributes = []
        
        for attr in product.attributes.all().select_related('attribute', 'attribute_value'):
            attributes.append({
                'attribute_id': str(attr.attribute.id),
                'attribute_name': attr.attribute.name,
                'value_id': str(attr.attribute_value.id),
                'value': attr.attribute_value.value,
                'color_code': attr.attribute_value.color_code,
                'image': attr.attribute_value.image.url if attr.attribute_value.image else None,
            })
        
        return JsonResponse({
            'product_id': str(product.id),
            'attributes': attributes
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)