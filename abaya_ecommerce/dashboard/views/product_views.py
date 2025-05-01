from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.forms import inlineformset_factory
from django.http import JsonResponse

from products.models import (
    Product, Category, ProductMedia, Size, Color, Fabric,
    ProductCategory, ProductFabric, ProductSize, FabricColor
)
from dashboard.forms import (
    ProductForm, ProductMediaForm, ProductVariantForm,
    SizeForm, ColorForm, FabricForm
)
from dashboard.models import DashboardActivity


@login_required
def product_list(request):
    """List all products with search and filter functionality"""
    # Get filter parameters
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')
    featured = request.GET.get('featured', '')
    
    # Base queryset
    products = Product.objects.select_related().prefetch_related('categories', 'media')
    
    # Apply filters
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(sku__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if category:
        products = products.filter(categories__id=category)
    
    if status:
        is_active = status == 'active'
        products = products.filter(is_active=is_active)
    
    if featured:
        is_featured = featured == 'yes'
        products = products.filter(is_featured=is_featured)
    
    # Ordering
    order_by = request.GET.get('order_by', '-created_at')
    if order_by == 'name':
        products = products.order_by('name')
    elif order_by == 'price':
        products = products.order_by('price')
    elif order_by == '-price':
        products = products.order_by('-price')
    elif order_by == 'sku':
        products = products.order_by('sku')
    else:
        products = products.order_by('-created_at')
    
    # Add default images to products
    for product in products:
        product.default_image = product.get_default_image()
    
    # Pagination
    paginator = Paginator(products, 15)
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Get all categories for filter dropdown
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'categories': categories,
        'filters': {
            'search': search,
            'category': category,
            'status': status,
            'featured': featured,
            'order_by': order_by
        }
    }
    
    return render(request, 'dashboard/products/list.html', context)


@login_required
def product_create(request):
    """Create a new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            # Save the product
            product = form.save()
            
            # Add categories
            for category in form.cleaned_data['categories']:
                ProductCategory.objects.create(product=product, category=category)
            
            # Add sizes
            for size in form.cleaned_data.get('sizes', []):
                ProductSize.objects.create(product=product, size=size)
            
            # Add fabrics
            for fabric in form.cleaned_data.get('fabrics', []):
                ProductFabric.objects.create(product=product, fabric=fabric)
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Created product',
                entity_type='Product',
                entity_id=str(product.id),
                details={'name': product.name, 'sku': product.sku}
            )
            
            messages.success(request, f'Product {product.name} created successfully.')
            
            # Redirect based on the "save_action" parameter
            save_action = request.POST.get('save_action', 'save')
            if save_action == 'save_and_add_images':
                return redirect('dashboard:product_images', pk=product.id)
            elif save_action == 'save_and_add_variants':
                return redirect('dashboard:product_variants', pk=product.id)
            elif save_action == 'save_and_add_another':
                return redirect('dashboard:product_create')
            else:
                return redirect('dashboard:product_list')
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'title': 'Create Product'
    }
    
    return render(request, 'dashboard/products/create.html', context)


@login_required
def product_edit(request, pk):
    """Edit an existing product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            # Track changes for activity log
            changed_fields = []
            for field in form.changed_data:
                if field not in ['categories', 'sizes', 'fabrics']:
                    orig_value = getattr(product, field) if hasattr(product, field) else None
                    changed_fields.append({
                        'field': field,
                        'old': str(orig_value),
                        'new': str(form.cleaned_data.get(field))
                    })
            
            # Save the product
            updated_product = form.save()
            
            # Update categories
            if 'categories' in form.changed_data:
                # Clear existing categories
                ProductCategory.objects.filter(product=product).delete()
                # Add new categories
                for category in form.cleaned_data['categories']:
                    ProductCategory.objects.create(product=product, category=category)
                
                changed_fields.append({
                    'field': 'categories',
                    'old': ', '.join(str(c.name) for c in product.categories.all()),
                    'new': ', '.join(str(c.name) for c in form.cleaned_data['categories'])
                })
            
            # Update sizes
            if 'sizes' in form.changed_data:
                # Clear existing sizes
                ProductSize.objects.filter(product=product).delete()
                # Add new sizes
                for size in form.cleaned_data.get('sizes', []):
                    ProductSize.objects.create(product=product, size=size)
                
                changed_fields.append({
                    'field': 'sizes',
                    'old': ', '.join(str(s.name) for s in product.sizes.all()),
                    'new': ', '.join(str(s.name) for s in form.cleaned_data.get('sizes', []))
                })
            
            # Update fabrics
            if 'fabrics' in form.changed_data:
                # Clear existing fabrics
                ProductFabric.objects.filter(product=product).delete()
                # Add new fabrics
                for fabric in form.cleaned_data.get('fabrics', []):
                    ProductFabric.objects.create(product=product, fabric=fabric)
                
                changed_fields.append({
                    'field': 'fabrics',
                    'old': ', '.join(str(f.name) for f in product.fabrics.all()),
                    'new': ', '.join(str(f.name) for f in form.cleaned_data.get('fabrics', []))
                })
            
            # Record activity with changes
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated product',
                entity_type='Product',
                entity_id=str(product.id),
                details={
                    'name': product.name,
                    'sku': product.sku,
                    'changes': changed_fields
                }
            )
            
            messages.success(request, f'Product {updated_product.name} updated successfully.')
            return redirect('dashboard:product_list')
    else:
        # Set initial values for many-to-many fields
        initial_data = {
            'categories': product.categories.all(),
            'sizes': product.sizes.all(),
            'fabrics': product.fabrics.all()
        }
        form = ProductForm(instance=product, initial=initial_data)
    
    # Get product images
    images = ProductMedia.objects.filter(product=product).order_by('sort_order')
    
    context = {
        'form': form,
        'product': product,
        'images': images,
        'title': f'Edit Product: {product.name}'
    }
    
    return render(request, 'dashboard/products/edit.html', context)


@login_required
def product_delete(request, pk):
    """Delete a product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product_id = str(product.id)
        
        # Delete the product
        product.delete()
        
        # Record activity
        DashboardActivity.objects.create(
            user=request.user,
            action='Deleted product',
            entity_type='Product',
            entity_id=product_id,
            details={'name': product_name}
        )
        
        messages.success(request, f'Product {product_name} deleted successfully.')
        return redirect('dashboard:product_list')
    
    context = {
        'product': product
    }
    
    return render(request, 'dashboard/products/delete.html', context)


@login_required
def product_images(request, pk):
    """Manage product images"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        # Check for delete action
        if 'delete_image' in request.POST:
            image_id = request.POST.get('delete_image')
            image = get_object_or_404(ProductMedia, id=image_id, product=product)
            image.delete()
            messages.success(request, 'Image deleted successfully.')
            return redirect('dashboard:product_images', pk=product.id)
        
        # Handle image form submission
        form = ProductMediaForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the image
            media = form.save(commit=False)
            media.product = product
            media.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Added product image',
                entity_type='ProductMedia',
                entity_id=str(media.id),
                details={
                    'product_name': product.name,
                    'product_id': str(product.id),
                    'is_default': media.is_default
                }
            )
            
            messages.success(request, 'Image added successfully.')
            return redirect('dashboard:product_images', pk=product.id)
    else:
        form = ProductMediaForm(initial={'is_default': not product.media.filter(is_default=True).exists()})
    
    # Get all product images
    images = ProductMedia.objects.filter(product=product).order_by('sort_order')
    
    context = {
        'form': form,
        'product': product,
        'images': images,
        'title': f'Manage Images for {product.name}'
    }
    
    return render(request, 'dashboard/products/images.html', context)


@login_required
def product_variants(request, pk):
    """Manage product variants (sizes, colors, fabrics)"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            fabric = form.cleaned_data.get('fabric')
            size = form.cleaned_data.get('size')
            colors = form.cleaned_data.get('colors', [])
            is_default = form.cleaned_data.get('is_default', False)
            
            # Add fabric to product if not already added
            if fabric:
                fabric_link, created = ProductFabric.objects.get_or_create(
                    product=product, fabric=fabric,
                    defaults={'is_default': is_default}
                )
                
                if not created and is_default:
                    fabric_link.is_default = True
                    fabric_link.save()
                
                # Add color-fabric relationships if not existing
                for color in colors:
                    FabricColor.objects.get_or_create(fabric=fabric, color=color)
            
            # Add size to product if not already added
            if size and not ProductSize.objects.filter(product=product, size=size).exists():
                ProductSize.objects.create(product=product, size=size)
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated product variants',
                entity_type='Product',
                entity_id=str(product.id),
                details={
                    'product_name': product.name,
                    'fabric': str(fabric.name) if fabric else None,
                    'size': str(size.name) if size else None,
                    'colors': [str(c.name) for c in colors]
                }
            )
            
            messages.success(request, 'Product variants updated successfully.')
            return redirect('dashboard:product_variants', pk=product.id)
    else:
        form = ProductVariantForm(initial={'product': product})
    
    # Get existing product fabrics, sizes, colors
    product_fabrics = ProductFabric.objects.filter(product=product).select_related('fabric')
    product_sizes = ProductSize.objects.filter(product=product).select_related('size')
    
    # Get fabric-color relationships
    fabric_colors = {}
    for pf in product_fabrics:
        colors = Color.objects.filter(fabrics=pf.fabric)
        fabric_colors[str(pf.fabric.id)] = list(colors.values('id', 'name', 'color_code'))
    
    context = {
        'form': form,
        'product': product,
        'product_fabrics': product_fabrics,
        'product_sizes': product_sizes,
        'fabric_colors': fabric_colors,
        'title': f'Manage Variants for {product.name}'
    }
    
    return render(request, 'dashboard/products/variants.html', context)


# Size Management Views
@login_required
def size_list(request):
    """List all sizes"""
    sizes = Size.objects.all().order_by('sort_order', 'name')
    
    # Get search parameter
    search = request.GET.get('search', '')
    if search:
        sizes = sizes.filter(name__icontains=search)
    
    # Pagination
    paginator = Paginator(sizes, 15)
    page = request.GET.get('page')
    try:
        sizes = paginator.page(page)
    except PageNotAnInteger:
        sizes = paginator.page(1)
    except EmptyPage:
        sizes = paginator.page(paginator.num_pages)
    
    context = {
        'sizes': sizes,
        'search': search
    }
    
    return render(request, 'dashboard/products/size_list.html', context)


@login_required
def size_create(request):
    """Create a new size"""
    if request.method == 'POST':
        form = SizeForm(request.POST)
        if form.is_valid():
            size = form.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Created size',
                entity_type='Size',
                entity_id=str(size.id),
                details={'name': size.name}
            )
            
            messages.success(request, f'Size {size.name} created successfully.')
            
            # Redirect based on the "save_action" parameter
            save_action = request.POST.get('save_action', 'save')
            if save_action == 'save_and_add_another':
                return redirect('dashboard:size_create')
            else:
                return redirect('dashboard:size_list')
    else:
        form = SizeForm()
    
    context = {
        'form': form,
        'title': 'Create Size'
    }
    
    return render(request, 'dashboard/products/size_form.html', context)


@login_required
def size_edit(request, pk):
    """Edit an existing size"""
    size = get_object_or_404(Size, pk=pk)
    
    if request.method == 'POST':
        form = SizeForm(request.POST, instance=size)
        if form.is_valid():
            updated_size = form.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated size',
                entity_type='Size',
                entity_id=str(size.id),
                details={'name': updated_size.name}
            )
            
            messages.success(request, f'Size {updated_size.name} updated successfully.')
            return redirect('dashboard:size_list')
    else:
        form = SizeForm(instance=size)
    
    context = {
        'form': form,
        'size': size,
        'title': f'Edit Size: {size.name}'
    }
    
    return render(request, 'dashboard/products/size_form.html', context)


@login_required
def size_delete(request, pk):
    """Delete a size"""
    size = get_object_or_404(Size, pk=pk)
    
    if request.method == 'POST':
        size_name = size.name
        size_id = str(size.id)
        
        # Check if size is used in products
        products_count = Product.objects.filter(sizes=size).count()
        if products_count > 0:
            messages.error(
                request, 
                f'Cannot delete size {size_name} as it is used in {products_count} products. ' +
                'Please remove it from all products first.'
            )
            return redirect('dashboard:size_list')
        
        # Delete the size
        size.delete()
        
        # Record activity
        DashboardActivity.objects.create(
            user=request.user,
            action='Deleted size',
            entity_type='Size',
            entity_id=size_id,
            details={'name': size_name}
        )
        
        messages.success(request, f'Size {size_name} deleted successfully.')
        return redirect('dashboard:size_list')
    
    context = {
        'size': size,
        'products_count': Product.objects.filter(sizes=size).count()
    }
    
    return render(request, 'dashboard/products/size_delete.html', context)


# Color Management Views
@login_required
def color_list(request):
    """List all colors"""
    colors = Color.objects.all().order_by('name')
    
    # Get search parameter
    search = request.GET.get('search', '')
    if search:
        colors = colors.filter(name__icontains=search)
    
    # Pagination
    paginator = Paginator(colors, 15)
    page = request.GET.get('page')
    try:
        colors = paginator.page(page)
    except PageNotAnInteger:
        colors = paginator.page(1)
    except EmptyPage:
        colors = paginator.page(paginator.num_pages)
    
    context = {
        'colors': colors,
        'search': search
    }
    
    return render(request, 'dashboard/products/color_list.html', context)


@login_required
def color_create(request):
    """Create a new color"""
    if request.method == 'POST':
        form = ColorForm(request.POST, request.FILES)
        if form.is_valid():
            color = form.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Created color',
                entity_type='Color',
                entity_id=str(color.id),
                details={'name': color.name}
            )
            
            messages.success(request, f'Color {color.name} created successfully.')
            
            # Redirect based on the "save_action" parameter
            save_action = request.POST.get('save_action', 'save')
            if save_action == 'save_and_add_another':
                return redirect('dashboard:color_create')
            else:
                return redirect('dashboard:color_list')
    else:
        form = ColorForm()
    
    context = {
        'form': form,
        'title': 'Create Color'
    }
    
    return render(request, 'dashboard/products/color_form.html', context)


@login_required
def color_edit(request, pk):
    """Edit an existing color"""
    color = get_object_or_404(Color, pk=pk)
    
    if request.method == 'POST':
        form = ColorForm(request.POST, request.FILES, instance=color)
        if form.is_valid():
            updated_color = form.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated color',
                entity_type='Color',
                entity_id=str(color.id),
                details={'name': updated_color.name}
            )
            
            messages.success(request, f'Color {updated_color.name} updated successfully.')
            return redirect('dashboard:color_list')
    else:
        form = ColorForm(instance=color)
    
    context = {
        'form': form,
        'color': color,
        'title': f'Edit Color: {color.name}'
    }
    
    return render(request, 'dashboard/products/color_form.html', context)


@login_required
def color_delete(request, pk):
    """Delete a color"""
    color = get_object_or_404(Color, pk=pk)
    
    if request.method == 'POST':
        color_name = color.name
        color_id = str(color.id)
        
        # Check if color is used in fabric-color relationships
        fabrics_count = FabricColor.objects.filter(color=color).count()
        if fabrics_count > 0:
            messages.error(
                request, 
                f'Cannot delete color {color_name} as it is assigned to {fabrics_count} fabrics. ' +
                'Please remove these relationships first.'
            )
            return redirect('dashboard:color_list')
        
        # Delete the color
        color.delete()
        
        # Record activity
        DashboardActivity.objects.create(
            user=request.user,
            action='Deleted color',
            entity_type='Color',
            entity_id=color_id,
            details={'name': color_name}
        )
        
        messages.success(request, f'Color {color_name} deleted successfully.')
        return redirect('dashboard:color_list')
    
    context = {
        'color': color,
        'fabrics_count': FabricColor.objects.filter(color=color).count()
    }
    
    return render(request, 'dashboard/products/color_delete.html', context)


# Fabric Management Views
@login_required
def fabric_list(request):
    """List all fabrics"""
    fabrics = Fabric.objects.all().order_by('name')
    
    # Get search parameter
    search = request.GET.get('search', '')
    if search:
        fabrics = fabrics.filter(name__icontains=search)
    
    # Pagination
    paginator = Paginator(fabrics, 15)
    page = request.GET.get('page')
    try:
        fabrics = paginator.page(page)
    except PageNotAnInteger:
        fabrics = paginator.page(1)
    except EmptyPage:
        fabrics = paginator.page(paginator.num_pages)
    
    context = {
        'fabrics': fabrics,
        'search': search
    }
    
    return render(request, 'dashboard/products/fabric_list.html', context)


@login_required
def fabric_create(request):
    """Create a new fabric"""
    if request.method == 'POST':
        form = FabricForm(request.POST)
        if form.is_valid():
            fabric = form.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Created fabric',
                entity_type='Fabric',
                entity_id=str(fabric.id),
                details={'name': fabric.name}
            )
            
            messages.success(request, f'Fabric {fabric.name} created successfully.')
            
            # Redirect based on the "save_action" parameter
            save_action = request.POST.get('save_action', 'save')
            if save_action == 'save_and_add_another':
                return redirect('dashboard:fabric_create')
            else:
                return redirect('dashboard:fabric_list')
    else:
        form = FabricForm()
    
    context = {
        'form': form,
        'title': 'Create Fabric'
    }
    
    return render(request, 'dashboard/products/fabric_form.html', context)


@login_required
def fabric_edit(request, pk):
    """Edit an existing fabric"""
    fabric = get_object_or_404(Fabric, pk=pk)
    
    if request.method == 'POST':
        form = FabricForm(request.POST, instance=fabric)
        if form.is_valid():
            updated_fabric = form.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated fabric',
                entity_type='Fabric',
                entity_id=str(fabric.id),
                details={'name': updated_fabric.name}
            )
            
            messages.success(request, f'Fabric {updated_fabric.name} updated successfully.')
            return redirect('dashboard:fabric_list')
    else:
        form = FabricForm(instance=fabric)
    
    # Get colors associated with this fabric
    colors = Color.objects.filter(fabrics=fabric)
    
    context = {
        'form': form,
        'fabric': fabric,
        'colors': colors,
        'title': f'Edit Fabric: {fabric.name}'
    }
    
    return render(request, 'dashboard/products/fabric_form.html', context)


@login_required
def fabric_delete(request, pk):
    """Delete a fabric"""
    fabric = get_object_or_404(Fabric, pk=pk)
    
    if request.method == 'POST':
        fabric_name = fabric.name
        fabric_id = str(fabric.id)
        
        # Check if fabric is used in products
        products_count = Product.objects.filter(fabrics=fabric).count()
        if products_count > 0:
            messages.error(
                request, 
                f'Cannot delete fabric {fabric_name} as it is used in {products_count} products. ' +
                'Please remove it from all products first.'
            )
            return redirect('dashboard:fabric_list')
        
        # Delete the fabric
        fabric.delete()
        
        # Record activity
        DashboardActivity.objects.create(
            user=request.user,
            action='Deleted fabric',
            entity_type='Fabric',
            entity_id=fabric_id,
            details={'name': fabric_name}
        )
        
        messages.success(request, f'Fabric {fabric_name} deleted successfully.')
        return redirect('dashboard:fabric_list')
    
    context = {
        'fabric': fabric,
        'products_count': Product.objects.filter(fabrics=fabric).count()
    }
    
    return render(request, 'dashboard/products/fabric_delete.html', context)