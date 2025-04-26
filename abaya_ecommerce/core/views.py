from django.shortcuts import render

# Create your views here.
# core/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse

from products.models import Product, Category, Currency
from .utils import log_activity, get_settings
from .forms import ContactForm, NewsletterForm

def home(request):
    """Display the home page with featured products, categories, etc."""
    # Get featured products
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    
    # Add default images to featured products
    for product in featured_products:
        product.default_image = product.get_default_image()
    
    # Get new arrivals
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    
    # Add default images to new arrivals
    for product in new_arrivals:
        product.default_image = product.get_default_image()
    
    # Get top categories
    top_categories = Category.objects.filter(is_active=True)[:6]
    
    # Get site settings
    settings = get_settings('site', public_only=True)
    
    # Log page view
    log_activity(request, 'viewed_home_page')
    
    return render(request, 'core/home.html', {
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'top_categories': top_categories,
        'settings': settings
    })

def about(request):
    """Display the about page."""
    # Get site settings
    settings = get_settings('site', public_only=True)
    
    # Log page view
    log_activity(request, 'viewed_about_page')
    
    return render(request, 'core/about.html', {
        'settings': settings
    })

def contact(request):
    """Display and process the contact form."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Send email
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            from django.core.mail import send_mail
            from django.conf import settings as django_settings
            
            admin_email = get_settings('email', key='admin_email', default=django_settings.DEFAULT_FROM_EMAIL)
            
            send_mail(
                f'Contact Form: {subject}',
                f'Name: {name}\nEmail: {email}\n\nMessage:\n{message}',
                django_settings.DEFAULT_FROM_EMAIL,
                [admin_email],
                fail_silently=False,
            )
            
            # Save activity log
            log_activity(request, 'submitted_contact_form', details=f"Subject: {subject}")
            
            messages.success(request, 'Your message has been sent successfully. We will contact you soon!')
            return redirect('contact')
    else:
        form = ContactForm()
    
    # Get site settings
    settings = get_settings('site', public_only=True)
    
    # Log page view
    log_activity(request, 'viewed_contact_page')
    
    return render(request, 'core/contact.html', {
        'form': form,
        'settings': settings
    })

def newsletter_signup(request):
    """Process newsletter signup form."""
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            name = form.cleaned_data.get('name', '')
            
            # In a real application, you would integrate with a newsletter service like Mailchimp
            # For now, just log the signup
            log_activity(request, 'newsletter_signup', details=f"Email: {email}")
            
            # Save to site settings for demo purposes
            from .models import Setting
            newsletter_emails = Setting.objects.filter(group='newsletter', key='subscribers').first()
            if newsletter_emails:
                import json
                subscribers = json.loads(newsletter_emails.value)
                subscribers.append({'email': email, 'name': name})
                newsletter_emails.value = json.dumps(subscribers)
                newsletter_emails.save()
            else:
                Setting.objects.create(
                    group='newsletter',
                    key='subscribers',
                    value=json.dumps([{'email': email, 'name': name}]),
                    type='JSON',
                    is_public=False
                )
            
            # Send confirmation email
            from django.core.mail import send_mail
            from django.conf import settings as django_settings
            from django.template.loader import render_to_string
            
            subject = 'Newsletter Subscription Confirmation'
            context = {
                'name': name or email.split('@')[0],
                'email': email,
                'site_name': get_settings('site', key='site_name', default='Abaya Ecommerce')
            }
            html_message = render_to_string('core/emails/newsletter_confirmation.html', context)
            plain_message = render_to_string('core/emails/newsletter_confirmation_plain.html', context)
            
            send_mail(
                subject,
                plain_message,
                django_settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=html_message,
                fail_silently=False
            )
            
            messages.success(request, 'Thank you for subscribing to our newsletter!')
            
            # If the form is submitted via AJAX, return a JSON response
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Thank you for subscribing to our newsletter!'})
            
            # Otherwise, redirect to the referrer or home page
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        else:
            # If the form is submitted via AJAX, return a JSON response with errors
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    
    # If not a POST request or not AJAX, redirect to home
    return redirect('home')

def error_404(request, exception):
    """Handle 404 errors."""
    return render(request, 'core/errors/404.html', status=404)

def error_500(request):
    """Handle 500 errors."""
    return render(request, 'core/errors/500.html', status=500)

def error_403(request, exception):
    """Handle 403 errors."""
    return render(request, 'core/errors/403.html', status=403)

def error_400(request, exception):
    """Handle 400 errors."""
    return render(request, 'core/errors/400.html', status=400)

def change_currency(request):
    """
    Change the currency and redirect back to the previous page.
    """
    if request.method == 'POST':
        currency_code = request.POST.get('currency_code')
        if currency_code:
            # Check if the currency exists and is active
            try:
                currency = Currency.objects.get(code=currency_code, is_active=True)
                request.session['currency_code'] = currency_code
            except Currency.DoesNotExist:
                pass
    
    # Redirect back to the referring page
    next_page = request.POST.get('next') or request.META.get('HTTP_REFERER', '/')
    return redirect(next_page)