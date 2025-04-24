# core/utils.py
import json
from django.utils import timezone
from .models import ActivityLog, Setting, EmailTemplate, EmailLog

def log_activity(request, action, entity_type=None, entity_id=None, details=None):
    """
    Log user activity.
    
    Args:
        request: The HTTP request
        action: Action performed (e.g., 'product_view', 'order_placed')
        entity_type: Type of entity (e.g., 'Product', 'Order')
        entity_id: ID of the entity
        details: Additional details as text
    """
    # Get user or None for anonymous users
    user = request.user if request.user.is_authenticated else None
    
    # Don't log activity for anonymous users
    if not user:
        return
    
    # Get IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Get user agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Create activity log
    ActivityLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )

def get_settings(group=None, key=None, default=None, public_only=False):
    """
    Get settings from the database.
    
    Args:
        group: Settings group (e.g., 'site', 'email')
        key: Specific setting key
        default: Default value if setting not found
        public_only: If True, only return public settings
        
    Returns:
        If group and key provided: Single setting value
        If only group provided: Dict of settings in that group
        If neither provided: Dict of all settings grouped by group
    """
    query = Setting.objects.all()
    
    if public_only:
        query = query.filter(is_public=True)
    
    if group and key:
        # Get specific setting
        try:
            setting = query.get(group=group, key=key)
            return setting.get_typed_value()
        except Setting.DoesNotExist:
            return default
    
    elif group:
        # Get all settings in group
        settings_dict = {}
        for setting in query.filter(group=group):
            settings_dict[setting.key] = setting.get_typed_value()
        return settings_dict
    
    else:
        # Get all settings grouped by group
        settings_dict = {}
        for setting in query:
            if setting.group not in settings_dict:
                settings_dict[setting.group] = {}
            settings_dict[setting.group][setting.key] = setting.get_typed_value()
        return settings_dict

def send_template_email(template_name, recipient, context=None, user=None):
    """
    Send an email using a template from the database.
    
    Args:
        template_name: Name of the template to use
        recipient: Email address of the recipient
        context: Dictionary of variables to use in the template
        user: User object (optional)
        
    Returns:
        True if the email was sent successfully, False otherwise
    """
    from django.core.mail import send_mail
    from django.template import Template, Context
    from django.conf import settings as django_settings
    
    try:
        # Get template
        template = EmailTemplate.objects.get(name=template_name, is_active=True)
        
        # Create context
        if context is None:
            context = {}
        
        # Add default context variables
        context['site_name'] = get_settings('site', key='site_name', default='Abaya Ecommerce')
        context['site_url'] = get_settings('site', key='site_url', default='https://example.com')
        
        # Render subject and content
        subject_template = Template(template.subject)
        html_template = Template(template.html_content)
        
        subject = subject_template.render(Context(context))
        html_content = html_template.render(Context(context))
        
        # Render plain text content if available
        text_content = None
        if template.text_content:
            text_template = Template(template.text_content)
            text_content = text_template.render(Context(context))
        
        # Send email
        send_mail(
            subject,
            text_content or html_content,
            django_settings.DEFAULT_FROM_EMAIL,
            [recipient],
            html_message=html_content,
            fail_silently=False
        )
        
        # Log email
        email_log = EmailLog.objects.create(
            template=template,
            recipient=recipient,
            subject=subject,
            body=html_content,
            user=user,
            status='SENT',
            sent_at=timezone.now()
        )
        
        return True
    
    except EmailTemplate.DoesNotExist:
        # Log error
        EmailLog.objects.create(
            template=None,
            recipient=recipient,
            subject=f"[Error] Template {template_name} not found",
            body="",
            user=user,
            status='FAILED',
            error_message=f"Email template '{template_name}' not found or is inactive."
        )
        return False
    
    except Exception as e:
        # Log error
        EmailLog.objects.create(
            template=None,
            recipient=recipient,
            subject=f"[Error] Failed to send email",
            body="",
            user=user,
            status='FAILED',
            error_message=str(e)
        )
        return False

def get_client_ip(request):
    """Get the client IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip