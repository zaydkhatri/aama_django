# dashboard/views/product_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction

from products.models import Product, Category, ProductCategory, ProductMedia, ProductFabric
from dashboard.forms import ProductForm, ProductMediaForm, ProductFilterForm
from dashboard.utils import staff_member_required, log_admin_activity, paginate_queryset

@staff_member_required
def product_list(request):
    """Display a list of products with search and filter options."""
    # Initialize filter form
    filter_form = ProductFilterForm(request.GET)
    
    # Get all products
    products = Product.objects.all().order_by('-created_at')
    
    # Apply filters if form is valid
    if filter_form.is_valid():
        # Search filter
        search = filter_form.cleaned_data.get('search')
        if search:
            products = products.filter(
                Q(name__icontains=search) | 
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Category filter
        category = filter_form.cleaned_data.get('category')
        if category:
            products = products.filter(categories=category)
        
        # Active status filter
        is_active = filter_form.cleaned_data.get('is_active')
        if is_active:
            products = products.filter(is_active=(is_active == '1'))
        
        # Featured filter
        is_featured = filter_form.cleaned_data.get('is_featured')
        if is_featured:
            products = products.filter(is_featured=(is_featured == '1'))
        
        # Price range filters
        price_min = filter_form.cleaned_data.get('price_min')
        if price_min is not None:
            products = products.filter(price__gte=price_min)
        
        price_max = filter_form.cleaned_data.get('price_max')
        if price_max is not None:
            products = products.filter(price__lte=price_max)
    
    # Add default image to each product
    for product in products:
        product.default_image = product.get_default_image()
    
    # Paginate results
    products = paginate_queryset(request, products, 10)
    
    return render(request, 'dashboard/products/list.html', {
        'products': products,
        'filter_form': filter_form,
    })

@staff_member_required
def product_detail(request, uuid):
    """Display detailed information about a product."""
    product = get_object_or_404(Product, id=uuid)
    
    # Get product images
    images = product.media.filter(type='IMAGE').order_by('sort_order')
    
    # Get product videos
    videos = product.media.filter(type='VIDEO').order_by('sort_order')
    
    # Get categories for this product
    categories = product.categories.all()
    
    # Get fabrics and sizes for this product
    fabrics = product.fabrics.all()
    sizes = product.sizes.all()
    
    # Get default image
    product.default_image = product.get_default_image()
    
    return render(request, 'dashboard/products/detail.html', {
        'product': product,
        'images': images,
        'videos': videos,
        'categories': categories,
        'fabrics': fabrics,
        'sizes': sizes,
    })

@staff_member_required
def product_create(request):
    """Create a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the product
                    product = form.save()
                    
                    # Associate categories
                    for category in form.cleaned_data['categories']:
                        ProductCategory.objects.create(product=product, category=category)
                    
                    # Associate fabrics
                    for fabric in form.cleaned_data['fabrics']:
                        # Set first fabric as default
                        is_default = (fabric == form.cleaned_data['fabrics'][0])
                        ProductFabric.objects.create(product=product, fabric=fabric, is_default=is_default)
                    
                    # Log activity
                    log_admin_activity(
                        request.user,
                        'CREATE',
                        'Product',
                        product.id,
                        f"Created product '{product.name}'",
                        request
                    )
                    
                    messages.success(request, f"Product '{product.name}' has been created successfully.")
                    return redirect('dashboard:product_media', uuid=product.id)
            except Exception as e:
                messages.error(request, f"Error creating product: {str(e)}")
    else:
        form = ProductForm()
    
    return render(request, 'dashboard/products/form.html', {
        'form': form,
        'title': 'Create Product',
    })

@staff_member_required
def product_edit(request, uuid):
    """Edit an existing product."""
    product = get_object_or_404(Product, id=uuid)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the product
                    product = form.save()
                    
                    # Update categories
                    ProductCategory.objects.filter(product=product).delete()
                    for category in form.cleaned_data['categories']:
                        ProductCategory.objects.create(product=product, category=category)
                    
                    # Update fabrics
                    current_fabrics = set(ProductFabric.objects.filter(product=product).values_list('fabric_id', flat=True))
                    new_fabrics = set(fabric.id for fabric in form.cleaned_data['fabrics'])
                    
                    # Remove fabrics that are no longer associated
                    fabrics_to_remove = current_fabrics - new_fabrics
                    ProductFabric.objects.filter(product=product, fabric_id__in=fabrics_to_remove).delete()
                    
                    # Add new fabrics
                    fabrics_to_add = new_fabrics - current_fabrics
                    for fabric_id in fabrics_to_add:
                        fabric = next(f for f in form.cleaned_data['fabrics'] if f.id == fabric_id)
                        # Set as default if there's no default or it's the first fabric
                        is_default = not ProductFabric.objects.filter(product=product, is_default=True).exists()
                        ProductFabric.objects.create(product=product, fabric=fabric, is_default=is_default)
                    
                    # Log activity
                    log_admin_activity(
                        request.user,
                        'UPDATE',
                        'Product',
                        product.id,
                        f"Updated product '{product.name}'",
                        request
                    )
                    
                    messages.success(request, f"Product '{product.name}' has been updated successfully.")
                    return redirect('dashboard:product_detail', uuid=product.id)
            except Exception as e:
                messages.error(request, f"Error updating product: {str(e)}")
    else:
        # Initialize form with category and fabric data
        initial_data = {
            'categories': product.categories.all(),
            'fabrics': product.fabrics.all(),
        }
        form = ProductForm(instance=product, initial=initial_data)
    
    return render(request, 'dashboard/products/form.html', {
        'form': form,
        'product': product,
        'title': f"Edit Product: {product.name}",
    })

@staff_member_required
def product_delete(request, uuid):
    """Delete a product."""
    product = get_object_or_404(Product, id=uuid)
    
    if request.method == 'POST':
        # Get product details for logging before deletion
        product_name = product.name
        product_id = str(product.id)
        
        # Delete the product
        product.delete()
        
        # Log activity
        log_admin_activity(
            request.user,
            'DELETE',
            'Product',
            product_id,
            f"Deleted product '{product_name}'",
            request
        )
        
        messages.success(request, f"Product '{product_name}' has been deleted successfully.")
        return redirect('dashboard:product_list')
    
    return render(request, 'dashboard/products/delete.html', {
        'product': product,
    })

@staff_member_required
def product_media(request, uuid):
    """Manage product media files."""
    product = get_object_or_404(Product, id=uuid)
    
    # Get product images
    images = product.media.filter(type='IMAGE').order_by('sort_order')
    
    # Get product videos
    videos = product.media.filter(type='VIDEO').order_by('sort_order')
    
    return render(request, 'dashboard/products/media.html', {
        'product': product,
        'images': images,
        'videos': videos,
    })

@staff_member_required
def product_media_add(request, uuid):
    """Add media to a product."""
    product = get_object_or_404(Product, id=uuid)
    
    if request.method == 'POST':
        form = ProductMediaForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.product = product
            media.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'CREATE',
                'ProductMedia',
                media.id,
                f"Added media to product '{product.name}'",
                request
            )
            
            messages.success(request, "Media has been added successfully.")
            return redirect('dashboard:product_media', uuid=product.id)
    else:
        form = ProductMediaForm()
    
    return render(request, 'dashboard/products/media_form.html', {
        'form': form,
        'product': product,
        'title': f"Add Media to {product.name}",
    })

@staff_member_required
def product_media_delete(request, uuid, media_id):
    """Delete media from a product."""
    product = get_object_or_404(Product, id=uuid)
    media = get_object_or_404(ProductMedia, id=media_id, product=product)
    
    if request.method == 'POST':
        # Delete the media
        media.delete()
        
        # Log activity
        log_admin_activity(
            request.user,
            'DELETE',
            'ProductMedia',
            media_id,
            f"Deleted media from product '{product.name}'",
            request
        )
        
        messages.success(request, "Media has been deleted successfully.")
        return redirect('dashboard:product_media', uuid=product.id)
    
    return render(request, 'dashboard/products/media_delete.html', {
        'product': product,
        'media': media,
    })

@staff_member_required
def product_media_edit(request, uuid, media_id):
    """Edit a product media item, especially useful for setting default images."""
    product = get_object_or_404(Product, id=uuid)
    media = get_object_or_404(ProductMedia, id=media_id, product=product)
    
    if request.method == 'POST':
        # Handle setting as default
        if 'is_default' in request.POST and request.POST['is_default'] == 'true' and media.type == 'IMAGE':
            # First unset any existing default
            ProductMedia.objects.filter(product=product, is_default=True).update(is_default=False)
            
            # Set this image as default
            media.is_default = True
            media.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'UPDATE',
                'ProductMedia',
                media_id,
                f"Set image as default for product '{product.name}'",
                request
            )
            
            messages.success(request, "Default image has been updated.")
        
        # Handle other fields if needed (alt text, sort order)
        else:
            # If you want to add a form for editing other fields
            pass
            
        return redirect('dashboard:product_media', uuid=product.id)
    
    # GET request - show edit form (if needed)
    return redirect('dashboard:product_media', uuid=product.id)