# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('currency/change/', views.change_currency, name='change_currency'),
    path('newsletter/signup/', views.newsletter_signup, name='newsletter_signup'),
]