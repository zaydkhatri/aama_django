# Update the signals.py file in products app

# products/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from .models import Category, Product, ProductMedia, SEO, FabricColor, Size, ProductSize

@receiver(pre_save, sender=Category)
def ensure_category_slug(sender, instance, **kwargs):
    """Ensure category has a slug before saving."""
    if not instance.slug:
        instance.slug = slugify(instance.name)

@receiver(pre_save, sender=Product)
def ensure_product_slug(sender, instance, **kwargs):
    """Ensure product has a slug before saving."""
    if not instance.slug:
        instance.slug = slugify(instance.name)

@receiver(post_save, sender=Category)
def create_category_seo(sender, instance, created, **kwargs):
    """Create SEO entry for new categories."""
    if created:
        SEO.objects.create(
            entity_type='Category',
            entity_id=instance.id,
            title=instance.name,
            description=instance.description or f"Shop {instance.name} collection",
            keywords=instance.name,
            indexable=True
        )

@receiver(post_save, sender=Product)
def create_product_seo(sender, instance, created, **kwargs):
    """Create SEO entry for new products."""
    if created:
        SEO.objects.create(
            entity_type='Product',
            entity_id=instance.id,
            title=instance.name,
            description=instance.description or f"Buy {instance.name} online",
            keywords=instance.name,
            indexable=instance.is_active
        )
        
        # Auto-associate all existing sizes with this new product
        sizes = Size.objects.filter(is_active=True)
        for size in sizes:
            ProductSize.objects.get_or_create(
                product=instance,
                size=size
            )

@receiver(post_save, sender=Product)
def update_product_seo(sender, instance, created, **kwargs):
    """Update SEO entry when product is updated."""
    if not created:
        try:
            seo = SEO.objects.get(entity_type='Product', entity_id=instance.id)
            seo.title = instance.meta_title or instance.name
            seo.description = instance.meta_description or instance.description or f"Buy {instance.name} online"
            seo.keywords = instance.meta_keywords or instance.name
            seo.indexable = instance.is_active
            seo.save()
        except SEO.DoesNotExist:
            # Create if doesn't exist
            SEO.objects.create(
                entity_type='Product',
                entity_id=instance.id,
                title=instance.name,
                description=instance.description or f"Buy {instance.name} online",
                keywords=instance.name,
                indexable=instance.is_active
            )

@receiver(post_delete, sender=Product)
def delete_product_seo(sender, instance, **kwargs):
    """Delete SEO entry when product is deleted."""
    SEO.objects.filter(entity_type='Product', entity_id=instance.id).delete()

@receiver(post_delete, sender=Category)
def delete_category_seo(sender, instance, **kwargs):
    """Delete SEO entry when category is deleted."""
    SEO.objects.filter(entity_type='Category', entity_id=instance.id).delete()

@receiver(post_save, sender=FabricColor)
def sync_fabric_color_relationships(sender, instance, created, **kwargs):
    """
    When a fabric-color relationship is created, make sure the relationship
    is reflected in the Color.fabrics ManyToMany relation
    """
    if created:
        # Add the fabric to the color's fabrics if it's not already there
        instance.color.fabrics.add(instance.fabric)

# Add a new signal handler for Size to associate it with all products
@receiver(post_save, sender=Size)
def associate_size_with_all_products(sender, instance, created, **kwargs):
    """
    When a new size is created, associate it with all existing products.
    """
    if created:
        products = Product.objects.filter(is_active=True)
        for product in products:
            ProductSize.objects.get_or_create(
                product=product,
                size=instance
            )