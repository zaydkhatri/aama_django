from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Category, Product, ProductCategory, ProductMedia, 
    Currency, Review, ReviewImage, SEO, Page,
    Size, Color, Fabric, FabricColor, ProductFabric, ProductSize
)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description', 'is_active', 'image')
        }),
        (_('SEO Fields'), {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ('file', 'alt', 'type', 'is_default', 'sort_order')

class ProductCategoryInline(admin.TabularInline):
    model = ProductCategory
    extra = 1
    verbose_name = _('Category')
    verbose_name_plural = _('Categories')

class ProductFabricInline(admin.TabularInline):
    model = ProductFabric
    extra = 1
    fields = ('fabric', 'is_default')
    verbose_name = _('Fabric')
    verbose_name_plural = _('Fabrics')

class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 0
    verbose_name = _('Size')
    verbose_name_plural = _('Sizes')
    # Make fields read-only to prevent manual removal but still show associations
    readonly_fields = ('size',)
    can_delete = False  # Prevent deletion of associations
    
    def has_add_permission(self, request, obj=None):
        # Disable the add button since sizes are auto-assigned
        return False

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'price', 'sale_price', 'is_active', 'is_featured', 'created_at')
    list_filter = ('is_active', 'is_featured', 'created_at')
    search_fields = ('name', 'slug', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductMediaInline, ProductCategoryInline, ProductFabricInline, ProductSizeInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'sku', 'price', 'sale_price')
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_featured'),
        }),
        (_('SEO Fields'), {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def get_product_image(self, obj):
        default_image = obj.media.filter(is_default=True).first()
        if default_image:
            return format_html('<img src="{}" width="50" height="50" />', default_image.url)
        return "-"
    get_product_image.short_description = 'Image'

class SizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    ordering = ['sort_order', 'name']
    
    def save_model(self, request, obj, form, change):
        """Override save_model to ensure new sizes get associated with all products"""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        
        # If this is a new size, associate it with all products
        if is_new:
            from products.models import Product, ProductSize
            products = Product.objects.filter(is_active=True)
            for product in products:
                ProductSize.objects.get_or_create(
                    product=product,
                    size=obj
                )

class FabricColorInline(admin.TabularInline):
    model = FabricColor
    extra = 1
    verbose_name = _('Color')
    verbose_name_plural = _('Colors')

class FabricAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FabricColorInline]

class FabricInline(admin.TabularInline):
    model = FabricColor
    extra = 1
    verbose_name = _('Fabric')
    verbose_name_plural = _('Fabrics')
    fk_name = 'color'

class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_preview', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'color_code')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FabricInline]
    
    def color_preview(self, obj):
        if obj.color_code:
            return format_html('<div style="background-color: {}; width: 30px; height: 30px; border: 1px solid #ddd;"></div>', obj.color_code)
        elif obj.image:
            return format_html('<img src="{}" width="30" height="30" />', obj.image.url)
        return "-"
    color_preview.short_description = 'Color'

class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'exchange_rate', 'is_default', 'is_active', 'created_at')
    list_filter = ('is_default', 'is_active', 'created_at')
    search_fields = ('code', 'name')
    readonly_fields = ('created_at', 'updated_at')

class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 1
    fields = ('image',)

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_verified', 'is_published', 'created_at')
    list_filter = ('rating', 'is_verified', 'is_published', 'created_at')
    search_fields = ('product__name', 'user__email', 'title', 'review')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ReviewImageInline]

class SEOAdmin(admin.ModelAdmin):
    list_display = ('entity_type', 'title', 'indexable', 'created_at')
    list_filter = ('entity_type', 'indexable', 'created_at')
    search_fields = ('title', 'description', 'keywords')
    readonly_fields = ('created_at', 'updated_at')

class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'sort_order', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'slug', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')

# Register models
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Size, SizeAdmin)
admin.site.register(Fabric, FabricAdmin)
admin.site.register(Color, ColorAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(SEO, SEOAdmin)
admin.site.register(Page, PageAdmin)