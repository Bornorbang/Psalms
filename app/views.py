from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
import logging
import os
import uuid
import hmac
import hashlib
import requests as http_client
from datetime import timedelta

logger = logging.getLogger(__name__)
from .forms import UserRegistrationForm, UserLoginForm, CustomPasswordResetForm, CustomSetPasswordForm, UserProfileForm, PropertyForm, PropertyImageFormSet
from .models import User, EmailVerificationToken, Property, RentalAgreement, Invoice, Payment, PaymentReceipt, SiteSettings, BroadcastMessage
from .decorators import email_verified_required, tenant_required, landlord_required, agent_required, super_admin_required

def load_json_data(filename):
    """Helper function to load JSON data from static folder"""
    filepath = os.path.join(settings.BASE_DIR, 'static', 'data', filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def home(request):
    """Home page view with featured properties from database"""
    # Get featured properties (max 6)
    featured_properties = Property.objects.filter(
        is_featured=True,
        status='AVAILABLE'
    ).select_related('landlord', 'agent')[:6]
    
    # If not enough featured properties, get latest available properties
    if featured_properties.count() < 6:
        featured_properties = Property.objects.filter(
            status='AVAILABLE'
        ).select_related('landlord', 'agent').order_by('-created_at')[:6]
    
    # Load pagedata for features section (keep this from JSON for now)
    pagedata = load_json_data('pagedata.json')
    
    context = {
        'properties': featured_properties,
        'all_properties': featured_properties,
        'features': pagedata.get('features', []) if isinstance(pagedata, dict) else [],
    }
    return render(request, 'home.html', context)

def properties_list(request):
    """Properties listing page with database-driven filtering"""
    # Start with all available properties
    properties = Property.objects.filter(status__in=['AVAILABLE', 'PENDING']).select_related('landlord', 'agent')
    
    # Get filter parameters
    keyword = request.GET.get('keyword', '')
    location = request.GET.get('location', '')
    category = request.GET.get('category', '')
    listing_type = request.GET.get('status', '')  # Maps to listing_type (RENT/SALE)
    sort_order = request.GET.get('sort', 'none')
    bedrooms = request.GET.get('bedrooms', '')
    bathrooms = request.GET.get('bathrooms', '')
    price_range = request.GET.get('price_range', '')
    
    # Apply filters
    if keyword:
        properties = properties.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(city__icontains=keyword)
        )
    
    if location:
        properties = properties.filter(
            Q(city__icontains=location) |
            Q(state__icontains=location) |
            Q(address__icontains=location)
        )
    
    if category:
        # Map category to PropertyType
        category_map = {
            'apartment': 'APARTMENT',
            'house': 'HOUSE',
            'villa': 'VILLA',
            'office': 'OFFICE',
            'shop': 'SHOP',
            'warehouse': 'WAREHOUSE',
            'land': 'LAND'
        }
        property_type = category_map.get(category.lower())
        if property_type:
            properties = properties.filter(property_type=property_type)
    
    if listing_type:
        if listing_type.upper() in ['RENT', 'SALE']:
            properties = properties.filter(listing_type=listing_type.upper())

    if bedrooms:
        try:
            properties = properties.filter(bedrooms__gte=int(bedrooms))
        except ValueError:
            pass

    if bathrooms:
        try:
            properties = properties.filter(bathrooms__gte=int(bathrooms))
        except ValueError:
            pass

    if price_range:
        try:
            low, high = price_range.split('-')
            properties = properties.filter(price__gte=int(low), price__lte=int(high))
        except (ValueError, AttributeError):
            pass

    # Apply sorting
    if sort_order == 'asc':
        properties = properties.order_by('title')
    elif sort_order == 'desc':
        properties = properties.order_by('-title')
    elif sort_order == 'price_asc':
        properties = properties.order_by('price')
    elif sort_order == 'price_desc':
        properties = properties.order_by('-price')
    else:
        properties = properties.order_by('-created_at')  # Default: newest first
    
    # Pagination (12 properties per page)
    paginator = Paginator(properties, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get unique cities and types for filter options
    all_cities = Property.objects.values_list('city', flat=True).distinct().order_by('city')
    
    locations = [{'value': city, 'label': city} for city in all_cities if city]
    categories = [
        {'value': 'apartment', 'label': 'Apartment'},
        {'value': 'house', 'label': 'House'},
        # Add more property types here when needed
    ]
    statuses = [
        {'value': 'RENT', 'label': 'For Rent'},
        {'value': 'SALE', 'label': 'For Sale'},
    ]
    
    context = {
        'title': category.title() if category else 'Properties List',
        'description': 'Browse our curated selection of premium properties',
        'breadcrumb_links': [
            {'href': '/', 'text': 'Home'},
            {'href': '/properties', 'text': 'Property List'},
        ],
        'properties': page_obj,
        'page_obj': page_obj,
        'locations': locations,
        'categories': categories,
        'statuses': statuses,
    }
    return render(request, 'properties_list.html', context)

def property_detail(request, slug):
    """Property detail page with view counter"""
    # Get property with related data
    property_obj = get_object_or_404(
        Property.objects.select_related('landlord', 'agent')
        .prefetch_related('images', 'documents', 'property_amenities__amenity'),
        slug=slug
    )
    
    # Increment view counter
    property_obj.views_count += 1
    property_obj.save(update_fields=['views_count'])
    
    # Get amenities for this property
    amenities = [pa.amenity for pa in property_obj.property_amenities.all()]
    
    # Get similar properties (same type, different property)
    similar_properties = Property.objects.filter(
        property_type=property_obj.property_type,
        status='AVAILABLE'
    ).exclude(id=property_obj.id)[:3]
    
    context = {
        'property': property_obj,
        'amenities': amenities,
        'similar_properties': similar_properties,
        'site_settings': SiteSettings.get_settings(),
    }
    return render(request, 'property_detail.html', context)

def contact(request):
    """Contact page"""
    if request.method == 'POST':
        # Handle form submission (in a real app, you would save to database or send email)
        pass
    
    context = {
        'breadcrumb_links': [
            {'href': '/', 'text': 'Home'},
            {'href': '/contact/', 'text': 'Contact'},
        ],
    }
    return render(request, 'contact.html', context)

def about(request):
    """About page"""
    return render(request, 'about.html')

def signin(request):
    """Sign in page with authentication"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                
                # Redirect to dashboard after successful login
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('dashboard_redirect')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'auth/signin.html', {'form': form})

def signup(request):
    """Sign up page with user registration"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.email_verified = True
            user.save()
            
            # Log the user in
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your account has been created successfully.')
            return redirect('dashboard_redirect')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/signup.html', {'form': form})

def signout(request):
    """Sign out"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


def verify_email(request, token):
    """Verify user email with token"""
    try:
        verification_token = EmailVerificationToken.objects.get(token=token)
        
        if verification_token.is_valid:
            user = verification_token.user
            user.email_verified = True
            user.save()
            
            verification_token.is_used = True
            verification_token.save()
            
            messages.success(request, 'Your email has been verified successfully!')
            if request.user.is_authenticated:
                return redirect('home')
            else:
                return redirect('signin')
        else:
            messages.error(request, 'This verification link has expired or already been used.')
            return redirect('home')
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('home')


def resend_verification(request):
    """Resend email verification"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in first.')
        return redirect('signin')
    
    if request.user.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('home')
    
    # Delete old unused tokens
    EmailVerificationToken.objects.filter(user=request.user, is_used=False).delete()
    
    # Create new token
    token = str(uuid.uuid4())
    verification_token = EmailVerificationToken.objects.create(
        user=request.user,
        token=token,
        expires_at=timezone.now() + timedelta(hours=24)
    )
    
    # Send verification email
    verification_url = request.build_absolute_uri(
        reverse('verify_email', kwargs={'token': token})
    )
    send_mail(
        subject='Verify your email - Psalms Real Estate',
        message=f'Hi {request.user.first_name},\n\nPlease verify your email by clicking the link below:\n{verification_url}\n\nThis link will expire in 24 hours.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[request.user.email],
        fail_silently=True,
    )
    
    messages.success(request, 'Verification email has been sent. Please check your inbox.')
    return redirect('home')


def password_reset_request(request):
    """Request password reset"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            users = User.objects.filter(email=email)
            
            if users.exists():
                for user in users:
                    # Django's built-in password reset
                    from django.contrib.auth.tokens import default_token_generator
                    from django.utils.http import urlsafe_base64_encode
                    from django.utils.encoding import force_bytes
                    
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    reset_url = request.build_absolute_uri(
                        reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                    )
                    
                    send_mail(
                        subject='Password Reset - Psalms Real Estate',
                        message=f'Hi {user.first_name},\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you did not request this, please ignore this email.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
            
            messages.success(request, 'If an account exists with this email, you will receive password reset instructions.')
            return redirect('signin')
    else:
        form = CustomPasswordResetForm()
    
    return render(request, 'auth/password_reset.html', {'form': form})


def password_reset_confirm(request, uidb64, token):
    """Confirm password reset with token"""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset successfully. You can now log in.')
                return redirect('signin')
        else:
            form = CustomSetPasswordForm(user)
        
        return render(request, 'auth/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('password_reset_request')


@login_required
def profile_view(request, username=None):
    """View user profile"""
    if username:
        # Viewing another user's profile
        try:
            profile_user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('home')
    else:
        # Viewing own profile
        profile_user = request.user
    
    context = {
        'profile_user': profile_user,
        'is_own_profile': profile_user == request.user,
    }
    return render(request, 'profile/profile_view.html', context)


@login_required
def profile_edit(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            
            # If email changed, set email_verified to False
            if 'email' in form.changed_data:
                user.email_verified = False
                
                # Create new verification token
                token = str(uuid.uuid4())
                EmailVerificationToken.objects.create(
                    user=user,
                    token=token,
                    expires_at=timezone.now() + timedelta(hours=24)
                )
                
                # Send verification email
                verification_url = request.build_absolute_uri(
                    reverse('verify_email', kwargs={'token': token})
                )
                send_mail(
                    subject='Verify your new email - Psalms Real Estate',
                    message=f'Hi {user.first_name},\n\nYour email has been changed. Please verify your new email by clicking the link below:\n{verification_url}\n\nThis link will expire in 24 hours.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                messages.info(request, 'Email changed. Please check your inbox to verify your new email address.')
            
            user.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile_view')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'profile/profile_edit.html', context)


@login_required
def profile_completion_status(request):
    """Get profile completion status (AJAX endpoint)"""
    user = request.user
    
    fields_status = {
        'first_name': bool(user.first_name),
        'last_name': bool(user.last_name),
        'email': bool(user.email),
        'phone_number': bool(user.phone_number),
        'profile_picture': bool(user.profile_picture),
        'email_verified': user.email_verified,
    }
    
    completed = sum(fields_status.values())
    total = len(fields_status)
    percentage = int((completed / total) * 100)
    
    return render(request, 'profile/completion_widget.html', {
        'completion_percentage': percentage,
        'fields_status': fields_status,
        'is_complete': completed == total,
    })


@login_required
def dashboard_redirect(request):
    """Redirect users to their role-specific dashboard"""
    if request.user.is_tenant:
        return redirect('tenant_dashboard')
    elif request.user.is_landlord:
        return redirect('landlord_dashboard')
    elif request.user.is_agent:
        return redirect('agent_dashboard')
    elif request.user.is_super_admin:
        return redirect('admin_dashboard')
    else:
        messages.warning(request, 'No dashboard available for your account type.')
        return redirect('home')


@login_required
def switch_role(request, role):
    """Switch user's active role between TENANT and LANDLORD"""
    # Only allow switching between TENANT and LANDLORD
    if role not in [User.Role.TENANT, User.Role.LANDLORD]:
        messages.error(request, 'Invalid role specified.')
        return redirect('dashboard_redirect')
    
    # Agents and Super Admins cannot switch roles
    if request.user.role in [User.Role.AGENT, User.Role.SUPER_ADMIN]:
        messages.error(request, 'Role switching is not available for your account type.')
        return redirect('dashboard_redirect')
    
    # Switch the role
    if request.user.switch_role(role):
        role_name = 'Tenant' if role == User.Role.TENANT else 'Landlord'
        messages.success(request, f'Switched to {role_name} view.')
    else:
        messages.error(request, 'Failed to switch role.')
    
    # Redirect to appropriate dashboard
    return redirect('dashboard_redirect')


@tenant_required
def tenant_dashboard(request):
    """Tenant dashboard view"""
    user = request.user

    # Active rental agreements — only show once tenant has made a successful payment
    active_agreements = RentalAgreement.objects.filter(
        tenant=user, status='ACTIVE',
        invoices__status='PAID'
    ).distinct().select_related('rental_property')

    # Invoice stats
    all_invoices = Invoice.objects.filter(tenant=user)
    pending_invoices = all_invoices.filter(status__in=['SENT', 'OVERDUE'])
    overdue_invoices = all_invoices.filter(status='OVERDUE')
    paid_invoices = all_invoices.filter(status='PAID')
    total_due = pending_invoices.aggregate(total=Sum('amount'))['total'] or 0

    # Recent payments
    recent_payments = Payment.objects.filter(
        tenant=user, status='SUCCESS'
    ).select_related('invoice', 'invoice__rental_agreement__rental_property').order_by('-created_at')[:5]

    context = {
        'user': user,
        'active_agreements': active_agreements,
        'active_agreements_count': active_agreements.count(),
        'pending_invoices_count': pending_invoices.count(),
        'overdue_invoices_count': overdue_invoices.count(),
        'paid_invoices_count': paid_invoices.count(),
        'total_due': total_due,
        'recent_payments': recent_payments,
    }
    return render(request, 'dashboard/tenant_dashboard.html', context)


@landlord_required
def landlord_dashboard(request):
    """Landlord dashboard view"""
    user = request.user

    # Active rental agreements (this landlord) — only after tenant has paid
    active_agreements = RentalAgreement.objects.filter(
        landlord=user, status='ACTIVE',
        invoices__status='PAID'
    ).distinct().select_related('rental_property', 'tenant')

    # Payment stats for this landlord's properties
    received_payments = Payment.objects.filter(
        invoice__rental_agreement__landlord=user,
        status='SUCCESS'
    )
    total_received = received_payments.aggregate(total=Sum('amount'))['total'] or 0

    # Pending & overdue invoices for their properties
    pending_invoices = Invoice.objects.filter(
        rental_agreement__landlord=user,
        status__in=['SENT', 'OVERDUE']
    )
    overdue_invoices = Invoice.objects.filter(
        rental_agreement__landlord=user,
        status='OVERDUE'
    )
    total_pending = pending_invoices.aggregate(total=Sum('amount'))['total'] or 0

    # Recent payments received
    recent_payments = Payment.objects.filter(
        invoice__rental_agreement__landlord=user,
        status='SUCCESS'
    ).select_related(
        'invoice', 'tenant',
        'invoice__rental_agreement__rental_property'
    ).order_by('-created_at')[:5]

    context = {
        'user': user,
        'active_agreements': active_agreements,
        'active_tenants_count': active_agreements.count(),
        'total_received': total_received,
        'pending_invoices_count': pending_invoices.count(),
        'overdue_invoices_count': overdue_invoices.count(),
        'total_pending': total_pending,
        'recent_payments': recent_payments,
    }
    return render(request, 'dashboard/landlord_dashboard.html', context)


@agent_required
def agent_dashboard(request):
    """Agent dashboard view"""
    context = {
        'user': request.user,
    }
    return render(request, 'dashboard/agent_dashboard.html', context)


@landlord_required
def landlord_properties(request):
    """Properties assigned to this landlord by admin/agent"""
    user = request.user
    from .models import Property as PropertyModel
    properties = PropertyModel.objects.filter(
        landlord=user
    ).prefetch_related('images').order_by('-created_at')

    return render(request, 'dashboard/landlord_properties.html', {
        'properties': properties,
        'page_title': 'My Properties',
        'total_count': properties.count(),
    })


@landlord_required
def landlord_tenants(request):
    """All tenants for this landlord, across all agreements"""
    user = request.user

    agreements = RentalAgreement.objects.filter(
        landlord=user,
        invoices__status='PAID'
    ).distinct().select_related('tenant', 'rental_property').order_by(
        '-status', '-start_date'
    )

    active_count = agreements.filter(status='ACTIVE').count()
    total_count = agreements.count()

    return render(request, 'dashboard/landlord_tenants.html', {
        'agreements': agreements,
        'active_count': active_count,
        'total_count': total_count,
        'page_title': 'My Tenants',
    })


@landlord_required
def landlord_payments(request):
    """Payments received — landlord-specific view"""
    user = request.user

    payments = Payment.objects.filter(
        invoice__rental_agreement__landlord=user,
        status='SUCCESS',
    ).select_related(
        'invoice', 'tenant',
        'invoice__rental_agreement',
        'invoice__rental_agreement__rental_property',
    ).order_by('-processed_at', '-created_at')

    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    total_count = payments.count()

    pending_invoices_count = Invoice.objects.filter(
        rental_agreement__landlord=user,
        status__in=['SENT', 'OVERDUE']
    ).count()

    paginator = Paginator(payments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/landlord_payments.html', {
        'payments': page_obj,
        'page_obj': page_obj,
        'total_amount': total_amount,
        'total_count': total_count,
        'pending_invoices_count': pending_invoices_count,
        'page_title': 'Payments Received',
    })


@super_admin_required
def admin_dashboard(request):
    """Admin dashboard view"""
    # User statistics
    total_users = User.objects.count()
    tenant_count = User.objects.filter(role=User.Role.TENANT).count()
    landlord_count = User.objects.filter(role=User.Role.LANDLORD).count()
    agent_count = User.objects.filter(role=User.Role.AGENT).count()

    multi_role_users = User.objects.filter(roles__isnull=False).exclude(roles=[])
    multi_role_count = sum(1 for u in multi_role_users if len(u.roles) > 1)

    unverified_users = User.objects.filter(email_verified=False).count()

    # Property stats
    from .models import Property as PropertyModel
    active_properties_count = PropertyModel.objects.filter(status='AVAILABLE').count()
    total_properties_count = PropertyModel.objects.count()

    # Rental stats
    active_rentals_count = RentalAgreement.objects.filter(status='ACTIVE').count()

    # Financial stats
    total_received = Payment.objects.filter(status='SUCCESS').aggregate(
        total=Sum('amount')
    )['total'] or 0
    pending_invoices_count = Invoice.objects.filter(status__in=['SENT', 'OVERDUE']).count()
    amount_pending = Invoice.objects.filter(status__in=['SENT', 'OVERDUE']).aggregate(
        total=Sum('amount')
    )['total'] or 0

    # Recent payments (all)
    recent_payments = Payment.objects.filter(
        status='SUCCESS'
    ).select_related(
        'invoice', 'tenant',
        'invoice__rental_agreement__rental_property'
    ).order_by('-processed_at', '-created_at')[:5]

    context = {
        'user': request.user,
        'total_users': total_users,
        'tenant_count': tenant_count,
        'landlord_count': landlord_count,
        'agent_count': agent_count,
        'multi_role_count': multi_role_count,
        'unverified_users': unverified_users,
        'active_properties_count': active_properties_count,
        'total_properties_count': total_properties_count,
        'active_rentals_count': active_rentals_count,
        'total_received': total_received,
        'pending_invoices_count': pending_invoices_count,
        'amount_pending': amount_pending,
        'recent_payments': recent_payments,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


# ============================================================================
# PROPERTY MANAGEMENT VIEWS (AGENT/ADMIN)
# ============================================================================

@login_required
def property_add(request):
    """
    Agent/Admin view to add a new property
    Only agents and super_admins can access
    """
    # Check if user is agent or super_admin
    if not (request.user.is_agent or request.user.is_super_admin):
        messages.error(request, 'You do not have permission to add properties.')
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        formset = PropertyImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            # Save property and set created_by to current user
            property_obj = form.save(commit=False)
            property_obj.created_by = request.user
            
            # If agent uploaded and didn't assign to themselves, set as agent
            if request.user.is_agent and not property_obj.agent:
                property_obj.agent = request.user
            
            property_obj.save()
            
            # Save property images
            formset.instance = property_obj
            formset.save()
            
            messages.success(request, f'Property "{property_obj.title}" added successfully!')
            return redirect('agent_property_list')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            if formset.errors:
                messages.error(request, 'Please fix errors in the property images section.')
    else:
        form = PropertyForm()
        formset = PropertyImageFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'page_title': 'Add New Property',
    }
    return render(request, 'dashboard/property_add.html', context)


@login_required
def property_edit(request, slug):
    """
    Agent/Admin view to edit an existing property
    Agents can only edit properties they created
    """
    # Get property
    property_obj = get_object_or_404(Property, slug=slug)
    
    # Check permissions
    if request.user.is_agent:
        # Agents can only edit properties they created
        if property_obj.created_by != request.user:
            messages.error(request, 'You can only edit properties you uploaded.')
            return redirect('agent_property_list')
    elif not request.user.is_super_admin:
        # Only agents and super_admins can edit
        messages.error(request, 'You do not have permission to edit properties.')
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property_obj)
        formset = PropertyImageFormSet(request.POST, request.FILES, instance=property_obj)
        
        if form.is_valid() and formset.is_valid():
            property_obj = form.save()
            formset.save()
            
            messages.success(request, f'Property "{property_obj.title}" updated successfully!')
            return redirect('agent_property_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PropertyForm(instance=property_obj)
        formset = PropertyImageFormSet(instance=property_obj)
    
    context = {
        'form': form,
        'formset': formset,
        'property': property_obj,
        'page_title': f'Edit Property: {property_obj.title}',
    }
    return render(request, 'dashboard/property_edit.html', context)


@login_required
def property_delete(request, slug):
    """
    Agent/Admin view to delete a property
    Agents can only delete properties they created
    """
    property_obj = get_object_or_404(Property, slug=slug)
    
    # Check permissions
    if request.user.is_agent:
        if property_obj.created_by != request.user:
            messages.error(request, 'You can only delete properties you uploaded.')
            return redirect('agent_property_list')
    elif not request.user.is_super_admin:
        messages.error(request, 'You do not have permission to delete properties.')
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        title = property_obj.title
        property_obj.delete()
        messages.success(request, f'Property "{title}" has been deleted.')
        return redirect('agent_property_list')
    
    context = {
        'property': property_obj,
    }
    return render(request, 'dashboard/property_confirm_delete.html', context)


@login_required
def agent_property_list(request):
    """
    Agent/Admin view to see all properties they uploaded
    Agents see only their properties, admins see all
    """
    # Check permissions
    if not (request.user.is_agent or request.user.is_super_admin):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard_redirect')
    
    # Filter properties
    if request.user.is_super_admin:
        properties = Property.objects.all()
    else:
        properties = Property.objects.filter(created_by=request.user)
    
    # Apply filters from query params
    status = request.GET.get('status')
    if status:
        properties = properties.filter(status=status.upper())
    
    listing_type = request.GET.get('listing_type')
    if listing_type:
        properties = properties.filter(listing_type=listing_type.upper())
    
    search = request.GET.get('search')
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(city__icontains=search) |
            Q(address__icontains=search)
        )
    
    # Order by newest first
    properties = properties.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(properties, 10)  # 10 properties per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get counts for stats
    total_properties = properties.count()
    available_count = properties.filter(status='AVAILABLE').count()
    rented_count = properties.filter(status='RENTED').count()
    
    
    context = {
        'properties': page_obj,
        'page_obj': page_obj,
        'total_properties': total_properties,
        'available_count': available_count,
        'rented_count': rented_count,
        'page_title': 'My Properties',
    }
    return render(request, 'dashboard/agent_property_list.html', context)


# ============================================================================
# PAYMENT MANAGEMENT VIEWS
# ============================================================================

@login_required
@tenant_required
def tenant_invoices(request):
    """
    Tenant view to see all their invoices
    """
    # Get all invoices for the tenant
    invoices = Invoice.objects.filter(tenant=request.user).select_related(
        'rental_agreement',
        'rental_agreement__rental_property'
    ).order_by('-issue_date')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status.upper())
    
    # Pagination
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals
    total_invoices = invoices.count()
    pending_invoices = invoices.filter(status__in=['SENT', 'OVERDUE']).count()
    paid_invoices = invoices.filter(status='PAID').count()
    total_due = invoices.filter(status__in=['SENT', 'OVERDUE']).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    context = {
        'invoices': page_obj,
        'page_obj': page_obj,
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'paid_invoices': paid_invoices,
        'total_due': total_due,
        'page_title': 'My Invoices',
    }
    return render(request, 'dashboard/tenant_invoices.html', context)


@login_required
@tenant_required
def invoice_detail(request, invoice_number):
    """
    Invoice detail view with payment simulation buttons
    """
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            'rental_agreement',
            'rental_agreement__rental_property',
            'rental_agreement__landlord'
        ),
        invoice_number=invoice_number,
        tenant=request.user
    )
    
    # Get payment history for this invoice
    payments = invoice.payments.all().order_by('-created_at')
    
    context = {
        'invoice': invoice,
        'payments': payments,
        'page_title': f'Invoice #{invoice.invoice_number}',
    }
    return render(request, 'dashboard/invoice_detail.html', context)


@login_required
@tenant_required
def payment_initiate(request, invoice_number):
    """Initiate a Paystack payment for an invoice"""
    invoice = get_object_or_404(Invoice, invoice_number=invoice_number, tenant=request.user)

    if invoice.balance <= 0 or invoice.status == 'CANCELLED':
        messages.error(request, 'This invoice cannot be paid.')
        return redirect('invoice_detail', invoice_number=invoice.invoice_number)

    if request.method == 'POST':
        amount = invoice.balance
        # Paystack requires amount in kobo (1 NGN = 100 kobo)
        amount_kobo = int(amount * 100)

        # Unique reference tied to this invoice attempt
        payment_ref = f'PSK-{invoice_number}-{uuid.uuid4().hex[:8].upper()}'

        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        callback_url = request.build_absolute_uri(reverse('payment_callback'))

        payload = {
            'email': request.user.email,
            'amount': amount_kobo,
            'reference': payment_ref,
            'callback_url': callback_url,
            'currency': invoice.currency,
            'metadata': {
                'invoice_number': invoice.invoice_number,
                'tenant_id': str(request.user.id),
                'tenant_name': request.user.get_full_name(),
                'property': invoice.rental_agreement.rental_property.title,
            },
        }

        try:
            resp = http_client.post(
                'https://api.paystack.co/transaction/initialize',
                json=payload,
                headers=headers,
                timeout=30,
            )
            data = resp.json()

            if data.get('status') and data.get('data'):
                auth_url = data['data']['authorization_url']

                # Create a pending Payment record
                Payment.objects.create(
                    invoice=invoice,
                    tenant=request.user,
                    amount=amount,
                    currency=invoice.currency,
                    payment_method=Payment.PaymentMethod.PAYSTACK,
                    status=Payment.PaymentStatus.PENDING,
                    gateway_reference=payment_ref,
                    gateway_response=data['data'],
                    notes='Paystack payment initiated',
                )

                return redirect(auth_url)
            else:
                messages.error(
                    request,
                    'Could not initiate payment. Please try again or contact support.'
                )
        except Exception:
            messages.error(request, 'Payment gateway error. Please try again.')

    return redirect('invoice_detail', invoice_number=invoice.invoice_number)


@login_required
def payment_callback(request):
    """Handle Paystack redirect after payment"""
    reference = request.GET.get('reference') or request.GET.get('trxref')

    if not reference:
        messages.error(request, 'Invalid payment callback.')
        return redirect('tenant_invoices')

    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}

    try:
        resp = http_client.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers,
            timeout=30,
        )
        data = resp.json()

        if not (data.get('status') and data.get('data')):
            messages.error(request, 'Could not verify payment.')
            return redirect('tenant_invoices')

        transaction = data['data']
        txn_status = transaction.get('status')

        try:
            payment = Payment.objects.get(gateway_reference=reference)
        except Payment.DoesNotExist:
            messages.error(request, 'Payment record not found.')
            return redirect('tenant_invoices')

        if payment.tenant != request.user:
            messages.error(request, 'Unauthorized access.')
            return redirect('tenant_invoices')

        invoice_number = payment.invoice.invoice_number

        if txn_status == 'success' and payment.status != Payment.PaymentStatus.SUCCESS:
            payment.status = Payment.PaymentStatus.SUCCESS
            payment.processed_at = timezone.now()
            payment.gateway_response = transaction
            payment.save()

            receipt = PaymentReceipt.objects.create(
                payment=payment,
                issued_to=request.user,
            )
            _send_payment_success_email(payment, receipt)
            messages.success(
                request,
                f'Payment successful! Receipt #{receipt.receipt_number} has been issued.'
            )

        elif txn_status in ('failed', 'abandoned'):
            if payment.status == Payment.PaymentStatus.PENDING:
                payment.status = Payment.PaymentStatus.FAILED
                payment.gateway_response = transaction
                payment.save()
            messages.error(request, 'Payment was not successful. Please try again.')

        else:
            messages.info(request, f'Payment status: {txn_status}.')

        return redirect('invoice_detail', invoice_number=invoice_number)

    except Exception:
        messages.error(request, 'Error verifying payment. Please contact support.')
        return redirect('tenant_invoices')


@csrf_exempt
def paystack_webhook(request):
    """Handle Paystack webhook events (charge.success, etc.)"""
    if request.method != 'POST':
        return HttpResponse(status=405)

    # Verify Paystack HMAC-SHA512 signature
    signature = request.headers.get('X-Paystack-Signature', '')
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    computed = hmac.new(secret, request.body, hashlib.sha512).hexdigest()

    if not hmac.compare_digest(computed, signature):
        return HttpResponse(status=400)

    try:
        event = json.loads(request.body)
        event_type = event.get('event')
        txn_data = event.get('data', {})

        if event_type == 'charge.success':
            reference = txn_data.get('reference')
            if reference:
                try:
                    payment = Payment.objects.select_related(
                        'invoice', 'tenant'
                    ).get(gateway_reference=reference)

                    if payment.status != Payment.PaymentStatus.SUCCESS:
                        payment.status = Payment.PaymentStatus.SUCCESS
                        payment.processed_at = timezone.now()
                        payment.gateway_response = txn_data
                        payment.save()

                        if not hasattr(payment, 'receipt'):
                            receipt = PaymentReceipt.objects.create(
                                payment=payment,
                                issued_to=payment.tenant,
                            )
                            _send_payment_success_email(payment, receipt)
                except Payment.DoesNotExist:
                    pass
    except Exception:
        pass

    return HttpResponse(status=200)


def _send_payment_success_email(payment, receipt):
    """Send payment confirmation emails to tenant and landlord"""
    invoice = payment.invoice
    agreement = invoice.rental_agreement
    property_title = agreement.rental_property.title
    tenant = payment.tenant
    landlord = agreement.landlord

    # Email to tenant
    try:
        send_mail(
            subject=f'Payment Confirmed – {property_title}',
            message=(
                f'Hi {tenant.first_name},\n\n'
                f'Your rent payment has been confirmed.\n\n'
                f'Invoice:   {invoice.invoice_number}\n'
                f'Amount:    {payment.currency} {payment.amount:,.2f}\n'
                f'Receipt:   {receipt.receipt_number}\n'
                f'Property:  {property_title}\n'
                f'Date:      {payment.processed_at.strftime("%d %b %Y %H:%M") if payment.processed_at else "—"}\n\n'
                f'Thank you for your payment.\n\nPsalms Real Estate'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[tenant.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error('Payment confirmation email to tenant %s failed: %s', tenant.email, e)

    # Email to landlord
    try:
        send_mail(
            subject=f'Rent Payment Received – {property_title}',
            message=(
                f'Hi {landlord.first_name},\n\n'
                f'A rent payment has been received for {property_title}.\n\n'
                f'Tenant:     {tenant.get_full_name()}\n'
                f'Amount:     {payment.currency} {payment.amount:,.2f}\n'
                f'Invoice:    {invoice.invoice_number}\n'
                f'Reference:  {payment.payment_reference}\n\n'
                f'Psalms Real Estate'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[landlord.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error('Payment notification email to landlord %s failed: %s', landlord.email, e)


@login_required
def payment_history(request):
    """
    Payment history for all users (filtered by role)
    """
    if request.user.is_tenant:
        # Tenants see their own payments
        payments = Payment.objects.filter(tenant=request.user)
        page_title = 'My Payment History'
    elif request.user.is_landlord:
        # Landlords see payments for their properties
        payments = Payment.objects.filter(
            invoice__rental_agreement__landlord=request.user
        )
        page_title = 'Payment History (Received)'
    elif request.user.is_agent or request.user.is_super_admin:
        # Agents and admins see all payments
        payments = Payment.objects.all()
        page_title = 'All Payments'
    else:
        messages.error(request, 'You do not have permission to view payments.')
        return redirect('dashboard_redirect')
    
    # Select related data
    payments = payments.select_related(
        'invoice',
        'tenant',
        'invoice__rental_agreement',
        'invoice__rental_agreement__rental_property'
    ).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status.upper())
    
    # Pagination
    paginator = Paginator(payments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate stats
    total_payments = payments.count()
    successful_payments = payments.filter(status='SUCCESS').count()
    total_amount = payments.filter(status='SUCCESS').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'total_payments': total_payments,
        'successful_payments': successful_payments,
        'total_amount': total_amount,
        'page_title': page_title,
    }
    return render(request, 'dashboard/payment_history.html', context)


@login_required
def messages_inbox(request):
    """
    Inbox: shows broadcast messages relevant to the current user's role.
    Super admins see all messages they sent.
    """
    user = request.user
    if user.is_super_admin:
        msgs = BroadcastMessage.objects.filter(sent_by=user)
    else:
        # Use active_role so switching dashboards also switches which messages are shown
        role_map = {
            'TENANT': 'TENANTS',
            'LANDLORD': 'LANDLORDS',
            'AGENT': 'AGENTS',
        }
        user_cat = role_map.get(user.active_role, None)
        if user_cat:
            msgs = BroadcastMessage.objects.filter(
                recipient_category__in=['ALL', user_cat]
            )
        else:
            msgs = BroadcastMessage.objects.filter(recipient_category='ALL')

    return render(request, 'dashboard/messages_inbox.html', {
        'msgs': msgs,
        'page_title': 'Messages',
    })


@login_required
def messages_send(request):
    """
    Compose + send a broadcast message. Super admin only.
    """
    if not request.user.is_super_admin:
        messages.error(request, 'Only super admins can send broadcast messages.')
        return redirect('messages_inbox')

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        category = request.POST.get('recipient_category', 'ALL')

        if not subject or not body:
            messages.error(request, 'Subject and body are required.')
        elif category not in [c[0] for c in BroadcastMessage.RecipientCategory.choices]:
            messages.error(request, 'Invalid recipient category.')
        else:
            msg = BroadcastMessage.objects.create(
                subject=subject,
                body=body,
                recipient_category=category,
                sent_by=request.user,
            )
            messages.success(request, f'Message "{msg.subject}" sent to {msg.get_recipient_category_display()}.')
            return redirect('messages_inbox')

    return render(request, 'dashboard/messages_send.html', {
        'categories': BroadcastMessage.RecipientCategory.choices,
        'page_title': 'New Message',
    })


@login_required
def download_receipt(request, receipt_number):
    receipt = get_object_or_404(
        PaymentReceipt.objects.select_related(
            'payment',
            'payment__invoice',
            'payment__invoice__rental_agreement',
            'payment__invoice__rental_agreement__rental_property',
            'payment__invoice__rental_agreement__landlord',
            'issued_to',
        ),
        receipt_number=receipt_number
    )

    # Verify permission: tenant, landlord of the property, agent or admin
    payment = receipt.payment
    agreement = payment.invoice.rental_agreement
    if not (
        request.user == receipt.issued_to
        or request.user == agreement.landlord
        or request.user.is_agent
        or request.user.is_super_admin
    ):
        messages.error(request, 'You do not have permission to view this receipt.')
        return redirect('dashboard_redirect')

    context = {
        'receipt': receipt,
        'page_title': f'Receipt #{receipt.receipt_number}',
    }
    return render(request, 'dashboard/receipt_view.html', context)









