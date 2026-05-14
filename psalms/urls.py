"""
URL configuration for psalms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', views.home, name='home'),
    path('properties/properties-list/', views.properties_list, name='properties_list'),
    path('properties/properties-list/<slug:slug>/', views.property_detail, name='property_detail'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    
    # Authentication URLs
    path('auth/signin/', views.signin, name='signin'),
    path('auth/signup/', views.signup, name='signup'),
    path('auth/signout/', views.signout, name='signout'),
    path('auth/verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('auth/resend-verification/', views.resend_verification, name='resend_verification'),
    path('auth/password-reset/', views.password_reset_request, name='password_reset_request'),
    path('auth/password-reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # Profile URLs
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<str:username>/', views.profile_view, name='profile_view_user'),
    path('profile/completion/status/', views.profile_completion_status, name='profile_completion_status'),
    
    # Dashboard URLs
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('dashboard/switch-role/<str:role>/', views.switch_role, name='switch_role'),
    path('dashboard/tenant/', views.tenant_dashboard, name='tenant_dashboard'),
    path('dashboard/landlord/', views.landlord_dashboard, name='landlord_dashboard'),
    path('dashboard/agent/', views.agent_dashboard, name='agent_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Property Management URLs (Agent/Admin)
    path('dashboard/properties/', views.agent_property_list, name='agent_property_list'),
    path('dashboard/properties/add/', views.property_add, name='property_add'),
    path('dashboard/properties/edit/<slug:slug>/', views.property_edit, name='property_edit'),
    path('dashboard/properties/delete/<slug:slug>/', views.property_delete, name='property_delete'),
    
    # Payment & Invoice URLs
    path('dashboard/invoices/', views.tenant_invoices, name='tenant_invoices'),
    path('dashboard/invoices/<str:invoice_number>/', views.invoice_detail, name='invoice_detail'),
    path('dashboard/invoices/<str:invoice_number>/pay/', views.payment_simulate, name='payment_simulate'),
    path('dashboard/payments/', views.payment_history, name='payment_history'),
    path('dashboard/receipts/<str:receipt_number>/', views.download_receipt, name='download_receipt'),
    
    # Legacy URLs for backward compatibility
    path('signin/', views.signin, name='signin_legacy'),
    path('signup/', views.signup, name='signup_legacy'),
    path('signout/', views.signout, name='signout_legacy'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

