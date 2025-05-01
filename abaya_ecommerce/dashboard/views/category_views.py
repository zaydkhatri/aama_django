# dashboard/views/category_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse

from products.models import Category, Product
from dashboard.forms import CategoryForm
from dashboard.utils import staff_member_required, log_admin_activity

@staff_member_required
def category_list(request):
    """Display a list of categories with search and filter options."""
    search_query = request.GET.get('search', '')
    
    # Get all categories
    categories = Category.objects.all().order_by('name')
    
    # Apply search if provided
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Annotate with product count
    categories = categories.annotate(product_count=Count('products'))
    
    # Paginate results
    paginator = Paginator(categories, 20)  # Show 20 categories per page
    page = request.GET.get('page')
    categories = paginator.get_page(page)
    
    return render(request, 'dashboard/categories/list.html', {
        'categories': categories,
        'search_query': search_query,
    })

@staff_member_required
def category_create(request):
    """Create a new category."""
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'CREATE',
                'Category',
                category.id,
                f"Created category '{category.name}'",
                request
            )
            
            messages.success(request, f"Category '{category.name}' has been created successfully.")
            return redirect('dashboard:category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'dashboard/categories/form.html', {
        'form': form,
        'title': 'Create Category',
    })

@staff_member_required
def category_edit(request, uuid):
    """Edit an existing category."""
    category = get_object_or_404(Category, id=uuid)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            category = form.save()
            
            # Log activity
            log_admin_activity(
                request.user,
                'UPDATE',
                'Category',
                category.id,
                f"Updated category '{category.name}'",
                request
            )
            
            messages.success(request, f"Category '{category.name}' has been updated successfully.")
            return redirect('dashboard:category_list')
    else:
        form = CategoryForm(instance=category)
    
    # Get products in this category
    products = Product.objects.filter(categories=category)
    
    return render(request, 'dashboard/categories/form.html', {
        'form': form,
        'category': category,
        'products': products[:10],  # Limit to 10 products for display
        'products_count': products.count(),
        'title': f"Edit Category: {category.name}",
    })

@staff_member_required
def category_delete(request, uuid):
    """Delete a category."""
    category = get_object_or_404(Category, id=uuid)
    
    # Check if this category has products
    products_count = Product.objects.filter(categories=category).count()
    
    if request.method == 'POST':
        # Get category details for logging before deletion
        category_name = category.name
        category_id = str(category.id)
        
        # Delete the category
        category.delete()
        
        # Log activity
        log_admin_activity(
            request.user,
            'DELETE',
            'Category',
            category_id,
            f"Deleted category '{category_name}'",
            request
        )
        
        messages.success(request, f"Category '{category_name}' has been deleted successfully.")
        return redirect('dashboard:category_list')
    
    return render(request, 'dashboard/categories/delete.html', {
        'category': category,
        'products_count': products_count,
    })