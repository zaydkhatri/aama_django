from django.contrib import admin

# Register your models here.
# products/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Category, Product, ProductCategory, ProductMedia, Attribute, 
    AttributeValue, ProductAttribute, Currency, ProductPrice, Review, 
    ReviewImage, SEO, Page
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

class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1
    fields = ('attribute', 'attribute_value')

class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 1
    fields = ('currency', 'price', 'sale_price')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'price', 'sale_price', 'quantity', 'is_active', 'is_featured', 'created_at')
    list_filter = ('is_active', 'is_featured', 'created_at')
    search_fields = ('name', 'slug', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductMediaInline, ProductCategoryInline, ProductAttributeInline, ProductPriceInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'sku', 'price', 'sale_price', 'cost', 'quantity')
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

class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1
    fields = ('value', 'slug', 'color_code', 'image', 'sort_order')
    prepopulated_fields = {'slug': ('value',)}

class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [AttributeValueInline]

class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ('value', 'slug', 'attribute', 'sort_order', 'created_at')
    list_filter = ('attribute', 'created_at')
    search_fields = ('value', 'slug')
    prepopulated_fields = {'slug': ('value',)}
    readonly_fields = ('created_at', 'updated_at')

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
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(AttributeValue, AttributeValueAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(SEO, SEOAdmin)
admin.site.register(Page, PageAdmin)