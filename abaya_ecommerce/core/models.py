from django.db import models

# Create your models here.
# core/models.py
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

class Setting(models.Model):
    SETTING_TYPE_CHOICES = (
        ('TEXT', 'Text'),
        ('NUMBER', 'Number'),
        ('BOOLEAN', 'Boolean'),
        ('JSON', 'JSON'),
        ('HTML', 'HTML'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.CharField(max_length=100)  # General, Payment, Shipping, Email, etc.
    key = models.CharField(max_length=100)
    value = models.TextField()
    type = models.CharField(max_length=10, choices=SETTING_TYPE_CHOICES, default='TEXT')
    is_public = models.BooleanField(default=False)  # If true, can be accessed from frontend
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Setting'
        verbose_name_plural = 'Settings'
        unique_together = ('group', 'key')
    
    def __str__(self):
        return f"{self.group}.{self.key}"
    
    def get_typed_value(self):
        """Return the value converted to the appropriate type."""
        if self.type == 'NUMBER':
            try:
                if '.' in self.value:
                    return float(self.value)
                else:
                    return int(self.value)
            except (ValueError, TypeError):
                return 0
        elif self.type == 'BOOLEAN':
            return self.value.lower() in ('true', 'yes', '1', 'on')
        elif self.type == 'JSON':
            import json
            try:
                return json.loads(self.value)
            except:
                return {}
        else:
            return self.value


class EmailTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)  # order_confirmation, shipping_notification, etc.
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True, null=True)  # Plain text version
    variables = models.TextField(blank=True, null=True)  # JSON string of available variables for this template
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
    
    def __str__(self):
        return self.name


class EmailLog(models.Model):
    EMAIL_STATUS_CHOICES = (
        ('QUEUED', 'Queued'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('BOUNCED', 'Bounced'),
        ('OPENED', 'Opened'),
        ('CLICKED', 'Clicked'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, blank=True, null=True, related_name='logs')
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, blank=True, null=True, related_name='received_emails')
    status = models.CharField(max_length=10, choices=EMAIL_STATUS_CHOICES, default='QUEUED')
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    opened_at = models.DateTimeField(blank=True, null=True)
    clicked_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Email to {self.recipient} ({self.status})"


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=100, blank=True, null=True)  # Product, Order, etc.
    entity_id = models.CharField(max_length=255, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.action}"