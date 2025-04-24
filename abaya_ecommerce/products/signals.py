# products/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from .models import Category, Product, ProductMedia, SEO

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