from django.db import models

# products/models.py
import uuid
from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class Size(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)  # S, M, L, XL, etc.
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Size'
        verbose_name_plural = 'Sizes'

    def __str__(self):
        return self.name

class Fabric(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)  # Cotton, Silk, Chiffon, etc.
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Fabric'
        verbose_name_plural = 'Fabrics'

    def __str__(self):
        return self.name

class Color(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)  # Red, Blue, Green, etc.
    color_code = models.CharField(max_length=10, blank=True, null=True)  # Hex color code
    image = models.ImageField(upload_to='colors/', blank=True, null=True)  # For patterns or complex colors
    is_active = models.BooleanField(default=True)
    fabrics = models.ManyToManyField(Fabric, through='FabricColor', related_name='colors')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Color'
        verbose_name_plural = 'Colors'

    def __str__(self):
        return self.name

class FabricColor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fabric = models.ForeignKey(Fabric, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('fabric', 'color')
        verbose_name = 'Fabric Color'
        verbose_name_plural = 'Fabric Colors'
    
    def __str__(self):
        return f"{self.fabric.name} - {self.color.name}"

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='children')
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})
    
    def get_all_products(self):
        """Get all products in this category and its subcategories."""
        products = self.products.filter(is_active=True)
        for child in self.children.filter(is_active=True):
            products |= child.get_all_products()
        return products


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    categories = models.ManyToManyField(Category, through='ProductCategory', related_name='products')
    # New fields for the simplified attribute model
    fabrics = models.ManyToManyField(Fabric, through='ProductFabric', related_name='products')
    sizes = models.ManyToManyField(Size, through='ProductSize', related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})
    
    def get_discount_percentage(self):
        if self.sale_price and self.price > 0:
            discount = ((self.price - self.sale_price) / self.price) * 100
            return round(discount, 2)
        return 0
    
    def get_active_price(self):
        return self.sale_price if self.sale_price else self.price
    
    def get_rating(self):
        reviews = self.reviews.filter(is_published=True)
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 1)
        return 0
    
    def get_review_count(self):
        return self.reviews.filter(is_published=True).count()

    def get_default_image(self):
        """Get the default image for this product, with fallback mechanisms."""
        # Try to get the default image first
        default_image = self.media.filter(is_default=True, type='IMAGE').first()
        
        # If no default image is found, try to get the first image
        if not default_image:
            default_image = self.media.filter(type='IMAGE').first()
        
        # If we found an image, return the file
        if default_image and default_image.file:
            return default_image.file
        
        # If no image is found, return None
        return None

    def get_price_display(self, currency=None):
        """
        Get formatted display price with currency symbol.
        Uses the current price if sale_price is not available.
        """
        from core.currency_utils import convert_price, format_price, get_selected_currency_from_request
        
        # Get default currency and selected currency
        default_currency = Currency.objects.get(is_default=True)
        
        # If no currency provided, use selected currency
        if currency is None:
            currency = get_selected_currency_from_request()
        
        # Determine which price to use (sale price or regular price)
        price = self.sale_price if self.sale_price else self.price
        
        # Convert price if needed
        if default_currency and currency and default_currency.id != currency.id:
            price = convert_price(price, default_currency, currency)
        
        # Format with currency symbol and return
        return format_price(price, currency)

    def get_regular_price_display(self, currency=None):
        """
        Get formatted regular price with currency symbol.
        """
        from core.currency_utils import convert_price, format_price, get_selected_currency_from_request
        
        # Get default currency and selected currency
        default_currency = Currency.objects.get(is_default=True)
        
        # If no currency provided, use selected currency
        if currency is None:
            currency = get_selected_currency_from_request()
        
        # Convert price if needed
        price = self.price
        if default_currency and currency and default_currency.id != currency.id:
            price = convert_price(price, default_currency, currency)
        
        # Format with currency symbol and return
        return format_price(price, currency)

    def get_available_colors(self):
        """Get all available colors for this product based on assigned fabrics."""
        product_fabrics = self.product_fabrics.all()
        if not product_fabrics:
            return Color.objects.none()
            
        fabric_ids = [pf.fabric_id for pf in product_fabrics]
        return Color.objects.filter(fabrics__in=fabric_ids, is_active=True).distinct()


class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        unique_together = ('product', 'category')
    
    def __str__(self):
        return f"{self.product.name} - {self.category.name}"


class ProductFabric(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_fabrics')
    fabric = models.ForeignKey(Fabric, on_delete=models.CASCADE)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Product Fabric'
        verbose_name_plural = 'Product Fabrics'
        unique_together = ('product', 'fabric')
    
    def __str__(self):
        return f"{self.product.name} - {self.fabric.name}"
        
    def save(self, *args, **kwargs):
        # If this fabric is being set as default, unset default flag for other fabrics of this product
        if self.is_default:
            ProductFabric.objects.filter(
                product=self.product,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)


class ProductSize(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_sizes')
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Product Size'
        verbose_name_plural = 'Product Sizes'
        unique_together = ('product', 'size')
    
    def __str__(self):
        return f"{self.product.name} - {self.size.name}"


class ProductMedia(models.Model):
    MEDIA_TYPE_CHOICES = (
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='products/')
    url = models.URLField(max_length=255, blank=True, null=True)
    alt = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='IMAGE')
    is_default = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Product Media'
        verbose_name_plural = 'Product Media'
        ordering = ['sort_order', 'created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.id}"
    
    def save(self, *args, **kwargs):
        # If this media is being set as default, unset default flag for other media of this product
        if self.is_default:
            ProductMedia.objects.filter(
                product=self.product,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        # Set URL based on the file if not provided
        if not self.url and self.file:
            from django.contrib.sites.models import Site
            domain = Site.objects.get_current().domain
            self.url = f"https://{domain}{self.file.url}"
        
        super().save(*args, **kwargs)


class Currency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'
        ordering = ['-is_default', 'code']
    
    def __str__(self):
        return f"{self.code} ({self.name})"
    
    def save(self, *args, **kwargs):
        # If this currency is being set as default, unset default flag for other currencies
        if self.is_default:
            Currency.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=255, blank=True, null=True)
    review = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)  # Verified purchase review
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.rating} stars by {self.user.name}"


class ReviewImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='reviews/')
    url = models.URLField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Review Image'
        verbose_name_plural = 'Review Images'
    
    def __str__(self):
        return f"Image for review {self.review.id}"
    
    def save(self, *args, **kwargs):
        # Set URL based on the image if not provided
        if not self.url and self.image:
            from django.contrib.sites.models import Site
            domain = Site.objects.get_current().domain
            self.url = f"https://{domain}{self.image.url}"
        
        super().save(*args, **kwargs)


class SEO(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=50)  # Product, Category, Page, Blog, etc.
    entity_id = models.UUIDField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    keywords = models.CharField(max_length=255, blank=True, null=True)
    og_title = models.CharField(max_length=255, blank=True, null=True)  # Open Graph title
    og_description = models.TextField(blank=True, null=True)  # Open Graph description
    og_image = models.URLField(blank=True, null=True)  # Open Graph image URL
    twitter_card = models.CharField(max_length=100, blank=True, null=True)  # Twitter card type
    canonical_url = models.URLField(blank=True, null=True)  # Canonical URL
    structured_data = models.JSONField(blank=True, null=True)  # JSON-LD structured data
    indexable = models.BooleanField(default=True)  # Should be indexed by search engines
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'SEO'
        verbose_name_plural = 'SEO'
    
    def __str__(self):
        return f"SEO for {self.entity_type}: {self.title}"


class PageView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, blank=True, null=True)
    session_id = models.CharField(max_length=255)
    url = models.URLField()
    referrer = models.URLField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Page View'
        verbose_name_plural = 'Page Views'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"View of {self.url} at {self.created_at}"


class ProductView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, blank=True, null=True)
    session_id = models.CharField(max_length=255)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Product View'
        verbose_name_plural = 'Product Views'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"View of {self.product.name} at {self.created_at}"


class SearchQuery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.CharField(max_length=255)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, blank=True, null=True)
    session_id = models.CharField(max_length=255)
    results_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Search Query'
        verbose_name_plural = 'Search Queries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Search for '{self.query}' with {self.results_count} results"


class Page(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content = models.TextField()
    is_published = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Page'
        verbose_name_plural = 'Pages'
        ordering = ['sort_order', 'title']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('page_detail', kwargs={'slug': self.slug})