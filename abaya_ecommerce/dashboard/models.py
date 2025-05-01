# from django.db import models

# Create your models here.
from django.db import models
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()

class DashboardActivity(models.Model):
    """
    Model to track admin user activities in the dashboard
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_activities')
    action = models.CharField(max_length=255)  # e.g., 'Created category', 'Updated product'
    entity_type = models.CharField(max_length=100)  # e.g., 'Category', 'Product'
    entity_id = models.CharField(max_length=255)  # UUID or ID of the entity
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    details = models.JSONField(blank=True, null=True)  # Additional details about the activity
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Dashboard Activity'
        verbose_name_plural = 'Dashboard Activities'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.created_at}"


class DashboardSettings(models.Model):
    """
    Model to store dashboard-specific settings
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Dashboard Setting'
        verbose_name_plural = 'Dashboard Settings'
    
    def __str__(self):
        return self.key