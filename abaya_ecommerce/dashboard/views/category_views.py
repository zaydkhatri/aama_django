from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count
from django.urls import reverse

from products.models import Category, Product
from dashboard.forms import CategoryForm
from dashboard.models import DashboardActivity

@login_required
def category_list(request):
    """List all categories with search and filter functionality"""
    # Get filter parameters
    search = request.GET.get('search', '')
    parent = request.GET.get('parent', '')
    status = request.GET.get('status', '')
    
    # Base queryset
    categories = Category.objects.all()
    
    # Apply filters
    if search:
        categories = categories.filter(name__icontains=search)
    
    if parent:
        if parent == 'none':
            categories = categories.filter(parent__isnull=True)
        else:
            categories = categories.filter(parent_id=parent)
    
    if status:
        is_active = status == 'active'
        categories = categories.filter(is_active=is_active)
    
    # Add product count to categories
    categories = categories.annotate(product_count=Count('products'))
    
    # Ordering
    order_by = request.GET.get('order_by', 'name')
    if order_by == 'name':
        categories = categories.order_by('name')
    elif order_by == 'product_count':
        categories = categories.order_by('-product_count')
    elif order_by == 'created_at':
        categories = categories.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(categories, 15)
    page = request.GET.get('page')
    try:
        categories = paginator.page(page)
    except PageNotAnInteger:
        categories = paginator.page(1)
    except EmptyPage:
        categories = paginator.page(paginator.num_pages)
    
    # Get all parent categories for filter dropdown
    parent_categories = Category.objects.filter(parent__isnull=True)
    
    context = {
        'categories': categories,
        'parent_categories': parent_categories,
        'filters': {
            'search': search,
            'parent': parent,
            'status': status,
            'order_by': order_by
        }
    }
    
    return render(request, 'dashboard/categories/list.html', context)


@login_required
def category_create(request):
    """Create a new category"""
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            
            # Record activity
            DashboardActivity.objects.create(
                user=request.user,
                action='Created category',
                entity_type='Category',
                entity_id=str(category.id),
                details={'name': category.name}
            )
            
            messages.success(request, f'Category {category.name} created successfully.')
            
            # Redirect based on the "save_action" parameter
            save_action = request.POST.get('save_action', 'save')
            if save_action == 'save_and_add_another':
                return redirect('dashboard:category_create')
            else:
                return redirect('dashboard:category_list')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'title': 'Create Category'
    }
    
    return render(request, 'dashboard/categories/create.html', context)


@login_required
def category_edit(request, pk):
    """Edit an existing category"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            # Track changes for activity log
            changed_fields = []
            for field in form.changed_data:
                orig_value = getattr(category, field) if hasattr(category, field) else None
                if field == 'image' and category.image:
                    orig_value = category.image.url
                changed_fields.append({
                    'field': field,
                    'old': str(orig_value),
                    'new': str(form.cleaned_data.get(field))
                })
            
            # Save the form
            updated_category = form.save()
            
            # Record activity with changes
            DashboardActivity.objects.create(
                user=request.user,
                action='Updated category',
                entity_type='Category',
                entity_id=str(category.id),
                details={
                    'name': category.name,
                    'changes': changed_fields
                }
            )
            
            messages.success(request, f'Category {updated_category.name} updated successfully.')
            return redirect('dashboard:category_list')
    else:
        form = CategoryForm(instance=category)
    
    # Get products in this category
    products = Product.objects.filter(categories=category)
    
    context = {
        'form': form,
        'category': category,
        'products': products,
        'title': f'Edit Category: {category.name}'
    }
    
    return render(request, 'dashboard/categories/edit.html', context)


@login_required
def category_delete(request, pk):
    """Delete a category"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category_name = category.name
        category_id = str(category.id)
        
        # Check if category has any products
        products_count = Product.objects.filter(categories=category).count()
        if products_count > 0:
            messages.error(
                request, 
                f'Cannot delete category {category_name} as it contains {products_count} products. ' +
                'Please reassign products to another category first.'
            )
            return redirect('dashboard:category_list')
        
        # Check if category has child categories
        if category.children.exists():
            messages.error(
                request, 
                f'Cannot delete category {category_name} as it has child categories. ' +
                'Please delete or reassign child categories first.'
            )
            return redirect('dashboard:category_list')
        
        # Delete the category
        category.delete()
        
        # Record activity
        DashboardActivity.objects.create(
            user=request.user,
            action='Deleted category',
            entity_type='Category',
            entity_id=category_id,
            details={'name': category_name}
        )
        
        messages.success(request, f'Category {category_name} deleted successfully.')
        return redirect('dashboard:category_list')
    
    context = {
        'category': category,
        'products_count': Product.objects.filter(categories=category).count(),
        'children_count': category.children.count()
    }
    
    return render(request, 'dashboard/categories/delete.html', context)