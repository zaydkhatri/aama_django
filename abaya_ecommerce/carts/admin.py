from django.contrib import admin

# Register your models here.
# carts/admin.py
from django.contrib import admin
from .models import Cart, CartItem, Wishlist, WishlistItem, GuestCart, GuestCartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('product', 'quantity', 'get_total_price')
    readonly_fields = ('get_total_price',)
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price()}"
    get_total_price.short_description = 'Total'

class GuestCartItemInline(admin.TabularInline):
    model = GuestCartItem
    extra = 0
    fields = ('product', 'quantity', 'get_total_price')
    readonly_fields = ('get_total_price',)
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price()}"
    get_total_price.short_description = 'Total'

class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    fields = ('product', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_item_count', 'get_total_price', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__name')
    readonly_fields = ('created_at', 'updated_at', 'get_total_price', 'get_item_count')
    inlines = [CartItemInline]
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price()}"
    get_total_price.short_description = 'Total Price'
    
    def get_item_count(self, obj):
        return obj.get_item_count()
    get_item_count.short_description = 'Items'

@admin.register(GuestCart)
class GuestCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_key', 'get_item_count', 'get_total_price', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('session_key',)
    readonly_fields = ('created_at', 'updated_at', 'get_total_price', 'get_item_count')
    inlines = [GuestCartItemInline]
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price()}"
    get_total_price.short_description = 'Total Price'
    
    def get_item_count(self, obj):
        return obj.get_item_count()
    get_item_count.short_description = 'Items'

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_item_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__name')
    readonly_fields = ('created_at', 'updated_at', 'get_item_count')
    inlines = [WishlistItemInline]
    
    def get_item_count(self, obj):
        return obj.get_item_count()
    get_item_count.short_description = 'Items'