from django.db import models

# Create your models here.
# users/models.py
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('STAFF', 'Staff'),
        ('CUSTOMER', 'Customer'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    name = models.CharField(_('full name'), max_length=150)
    phone = models.CharField(_('phone number'), max_length=15, blank=True, null=True)
    role = models.CharField(_('role'), max_length=15, choices=ROLE_CHOICES, default='CUSTOMER')
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_expiry = models.DateTimeField(blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, blank=True, null=True)
    password_reset_expiry = models.DateTimeField(blank=True, null=True)
    
    login_attempts = models.IntegerField(default=0)
    last_login_attempt = models.DateTimeField(blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return self.name
    
    def get_short_name(self):
        return self.name.split()[0] if self.name else self.email
    
    def is_admin(self):
        return self.role == 'ADMIN'
    
    def is_staff_member(self):
        return self.role == 'STAFF'
    
    def increment_login_attempts(self):
        self.login_attempts += 1
        self.last_login_attempt = timezone.now()
        self.save(update_fields=['login_attempts', 'last_login_attempt'])
    
    def reset_login_attempts(self):
        self.login_attempts = 0
        self.save(update_fields=['login_attempts'])
    
    def is_locked_out(self):
        if self.login_attempts >= 5 and self.last_login_attempt:
            lockout_time = timezone.timedelta(minutes=5)
            return timezone.now() - self.last_login_attempt < lockout_time
        return False


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token = models.CharField(max_length=255, unique=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session for {self.user.email}"
    
    def is_expired(self):
        return timezone.now() >= self.expires_at


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    email_marketing = models.BooleanField(default=True)
    email_order_updates = models.BooleanField(default=True)
    email_returns = models.BooleanField(default=True)
    email_account = models.BooleanField(default=True)
    sms_marketing = models.BooleanField(default=False)
    sms_order_updates = models.BooleanField(default=True)
    sms_returns = models.BooleanField(default=False)
    sms_account = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"


class Address(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('SHIPPING', 'Shipping'),
        ('BILLING', 'Billing'),
        ('BOTH', 'Both'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    address_type = models.CharField(max_length=15, choices=ADDRESS_TYPE_CHOICES, default='SHIPPING')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.state}, {self.country}"
    
    def save(self, *args, **kwargs):
        # If this address is being set as default, unset default flag for other addresses of same type
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
            
            # If address type is BOTH, unset default for both SHIPPING and BILLING
            if self.address_type == 'BOTH':
                Address.objects.filter(
                    user=self.user,
                    address_type__in=['SHIPPING', 'BILLING'],
                    is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)