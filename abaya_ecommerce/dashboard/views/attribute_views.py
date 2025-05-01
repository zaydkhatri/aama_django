# dashboard/views/attribute_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction

from products.models import Size, Color, Fabric, FabricColor
from dashboard.forms import SizeForm, ColorForm, FabricForm
from dashboard.utils import staff_member_required, log_admin_activity, paginate_queryset

# Size Management Views
@staff_member_required
def size_list(request):
    """Display a list of product sizes."""
    # Get all sizes
    sizes = Size.objects.all().order_by('sort_order', 'name')
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        sizes = sizes.filter(name__icontains=search_query)
    
    # Annotate with product count
    sizes = sizes.annotate(product_count=Count('products'))
    
    # Paginate results
    sizes = paginate_queryset(request, sizes, 20)
    
    return render(request, 'dashboard/attributes/size_list.html', {
        'sizes': sizes,
        'search_query': search_query,
    })

@staff_member_required
def size_create(request):
    """Create a new size."""
    if request.method == 'POST':
        form = SizeForm(request.POST)
        if form.is_valid():
            size = form.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'CREATE',
                'Size',
                size.id,
                f"Created size '{size.name}'",
                request
            )
            
            messages.success(request, f"Size '{size.name}' has been created successfully.")
            return redirect('dashboard:size_list')
    else:
        form = SizeForm()
    
    return render(request, 'dashboard/attributes/size_form.html', {
        'form': form,
        'title': 'Create Size',
    })

@staff_member_required
def size_edit(request, uuid):
    """Edit an existing size."""
    size = get_object_or_404(Size, id=uuid)
    
    if request.method == 'POST':
        form = SizeForm(request.POST, instance=size)
        if form.is_valid():
            size = form.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'UPDATE',
                'Size',
                size.id,
                f"Updated size '{size.name}'",
                request
            )
            
            messages.success(request, f"Size '{size.name}' has been updated successfully.")
            return redirect('dashboard:size_list')
    else:
        form = SizeForm(instance=size)
    
    # Count products using this size
    product_count = size.products.count()
    
    return render(request, 'dashboard/attributes/size_form.html', {
        'form': form,
        'size': size,
        'product_count': product_count,
        'title': f"Edit Size: {size.name}",
    })

@staff_member_required
def size_delete(request, uuid):
    """Delete a size."""
    size = get_object_or_404(Size, id=uuid)
    
    # Count products using this size
    product_count = size.products.count()
    
    if request.method == 'POST':
        # Get size details for logging before deletion
        size_name = size.name
        size_id = str(size.id)
        
        # Delete the size
        size.delete()
        
        # Log activity
        log_admin_activity(
            request.user,
            'DELETE',
            'Size',
            size_id,
            f"Deleted size '{size_name}'",
            request
        )
        
        messages.success(request, f"Size '{size_name}' has been deleted successfully.")
        return redirect('dashboard:size_list')
    
    return render(request, 'dashboard/attributes/size_delete.html', {
        'size': size,
        'product_count': product_count,
    })

# Fabric Management Views
@staff_member_required
def fabric_list(request):
    """Display a list of fabrics."""
    # Get all fabrics
    fabrics = Fabric.objects.all().order_by('name')
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        fabrics = fabrics.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Annotate with product count and color count
    fabrics = fabrics.annotate(
        product_count=Count('products', distinct=True),
        color_count=Count('colors', distinct=True)
    )
    
    # Paginate results
    fabrics = paginate_queryset(request, fabrics, 20)
    
    return render(request, 'dashboard/attributes/fabric_list.html', {
        'fabrics': fabrics,
        'search_query': search_query,
    })

@staff_member_required
def fabric_create(request):
    """Create a new fabric."""
    if request.method == 'POST':
        form = FabricForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                fabric = form.save()
                
                # Associate colors
                colors = form.cleaned_data.get('colors', [])
                for color in colors:
                    FabricColor.objects.create(fabric=fabric, color=color)
                
                # Log activity
                log_admin_activity(
                    request.user,
                    'CREATE',
                    'Fabric',
                    fabric.id,
                    f"Created fabric '{fabric.name}'",
                    request
                )
                
                messages.success(request, f"Fabric '{fabric.name}' has been created successfully.")
                return redirect('dashboard:fabric_list')
    else:
        form = FabricForm()
    
    return render(request, 'dashboard/attributes/fabric_form.html', {
        'form': form,
        'title': 'Create Fabric',
    })

@staff_member_required
def fabric_edit(request, uuid):
    """Edit an existing fabric."""
    fabric = get_object_or_404(Fabric, id=uuid)
    
    if request.method == 'POST':
        form = FabricForm(request.POST, instance=fabric)
        if form.is_valid():
            with transaction.atomic():
                fabric = form.save()
                
                # Update colors
                # Get current colors
                current_colors = set(FabricColor.objects.filter(fabric=fabric).values_list('color_id', flat=True))
                # Get new colors
                new_colors = set(color.id for color in form.cleaned_data.get('colors', []))
                
                # Colors to remove
                colors_to_remove = current_colors - new_colors
                FabricColor.objects.filter(fabric=fabric, color_id__in=colors_to_remove).delete()
                
                # Colors to add
                colors_to_add = new_colors - current_colors
                for color_id in colors_to_add:
                    color = next(c for c in form.cleaned_data.get('colors', []) if c.id == color_id)
                    FabricColor.objects.create(fabric=fabric, color=color)
                
                # Log activity
                log_admin_activity(
                    request.user,
                    'UPDATE',
                    'Fabric',
                    fabric.id,
                    f"Updated fabric '{fabric.name}'",
                    request
                )
                
                messages.success(request, f"Fabric '{fabric.name}' has been updated successfully.")
                return redirect('dashboard:fabric_list')
    else:
        # Initialize with colors data
        form = FabricForm(
            instance=fabric,
            initial={'colors': fabric.colors.all()}
        )
    
    # Count products using this fabric
    product_count = fabric.products.count()
    
    return render(request, 'dashboard/attributes/fabric_form.html', {
        'form': form,
        'fabric': fabric,
        'product_count': product_count,
        'title': f"Edit Fabric: {fabric.name}",
    })

@staff_member_required
def fabric_delete(request, uuid):
    """Delete a fabric."""
    fabric = get_object_or_404(Fabric, id=uuid)
    
    # Count products using this fabric
    product_count = fabric.products.count()
    
    if request.method == 'POST':
        # Get fabric details for logging before deletion
        fabric_name = fabric.name
        fabric_id = str(fabric.id)
        
        # Delete the fabric
        fabric.delete()
        
        # Log activity
        log_admin_activity(
            request.user,
            'DELETE',
            'Fabric',
            fabric_id,
            f"Deleted fabric '{fabric_name}'",
            request
        )
        
        messages.success(request, f"Fabric '{fabric_name}' has been deleted successfully.")
        return redirect('dashboard:fabric_list')
    
    return render(request, 'dashboard/attributes/fabric_delete.html', {
        'fabric': fabric,
        'product_count': product_count,
    })

# Color Management Views
@staff_member_required
def color_list(request):
    """Display a list of colors."""
    # Get all colors
    colors = Color.objects.all().order_by('name')
    
    # Apply search if provided
    search_query = request.GET.get('search', '')
    if search_query:
        colors = colors.filter(name__icontains=search_query)
    
    # Annotate with fabric count
    colors = colors.annotate(fabric_count=Count('fabrics', distinct=True))
    
    # Paginate results
    colors = paginate_queryset(request, colors, 20)
    
    return render(request, 'dashboard/attributes/color_list.html', {
        'colors': colors,
        'search_query': search_query,
    })

@staff_member_required
def color_create(request):
    """Create a new color."""
    if request.method == 'POST':
        form = ColorForm(request.POST, request.FILES)
        if form.is_valid():
            color = form.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'CREATE',
                'Color',
                color.id,
                f"Created color '{color.name}'",
                request
            )
            
            messages.success(request, f"Color '{color.name}' has been created successfully.")
            return redirect('dashboard:color_list')
    else:
        form = ColorForm()
    
    return render(request, 'dashboard/attributes/color_form.html', {
        'form': form,
        'title': 'Create Color',
    })

@staff_member_required
def color_edit(request, uuid):
    """Edit an existing color."""
    color = get_object_or_404(Color, id=uuid)
    
    if request.method == 'POST':
        form = ColorForm(request.POST, request.FILES, instance=color)
        if form.is_valid():
            color = form.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'UPDATE',
                'Color',
                color.id,
                f"Updated color '{color.name}'",
                request
            )
            
            messages.success(request, f"Color '{color.name}' has been updated successfully.")
            return redirect('dashboard:color_list')
    else:
        form = ColorForm(instance=color)
    
    # Get fabrics using this color
    fabrics = color.fabrics.all()
    
    return render(request, 'dashboard/attributes/color_form.html', {
        'form': form,
        'color': color,
        'fabrics': fabrics,
        'title': f"Edit Color: {color.name}",
    })

@staff_member_required
def color_delete(request, uuid):
    """Delete a color."""
    color = get_object_or_404(Color, id=uuid)
    
    # Get fabrics using this color
    fabrics = color.fabrics.all()
    fabrics_count = fabrics.count()
    
    if request.method == 'POST':
        # Get color details for logging before deletion
        color_name = color.name
        color_id = str(color.id)
        
        # Delete the color
        color.delete()
        
        # Log activity
        log_admin_activity(
            request.user,
            'DELETE',
            'Color',
            color_id,
            f"Deleted color '{color_name}'",
            request
        )
        
        messages.success(request, f"Color '{color_name}' has been deleted successfully.")
        return redirect('dashboard:color_list')
    
    return render(request, 'dashboard/attributes/color_delete.html', {
        'color': color,
        'fabrics': fabrics,
        'fabrics_count': fabrics_count,
    })