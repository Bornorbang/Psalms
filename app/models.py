from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from ckeditor_uploader.fields import RichTextUploadingField
import uuid
import random

# Create your models here.

class User(AbstractUser):
    """
    Custom User model with role-based access control
    Roles: Tenant, Landlord, Agent/Admin, Super Admin
    """
    
    class Role(models.TextChoices):
        TENANT = 'TENANT', _('Tenant')
        LANDLORD = 'LANDLORD', _('Landlord')
        AGENT = 'AGENT', _('Agent/Admin')
        SUPER_ADMIN = 'SUPER_ADMIN', _('Super Admin')
    
    user_id = models.CharField(
        max_length=4,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Unique 4-digit user ID')
    )
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TENANT,
        help_text=_('Primary user role for access control')
    )
    
    # Multi-role support
    roles = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of user roles for multi-role access')
    )
    
    active_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        blank=True,
        help_text=_('Currently active role (for role switching)')
    )
    
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_('Contact phone number')
    )
    
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text=_('User profile picture')
    )
    
    email_verified = models.BooleanField(
        default=False,
        help_text=_('Email verification status')
    )
    
    # KYC/ID Verification
    ID_TYPE_CHOICES = [
        ('NATIONAL_ID', 'National ID'),
        ('DRIVERS_LICENSE', 'Driver\'s License'),
        ('PASSPORT', 'International Passport'),
        ('VOTERS_CARD', 'Voter\'s Card'),
    ]
    
    id_type = models.CharField(
        max_length=20,
        choices=ID_TYPE_CHOICES,
        blank=True,
        help_text=_('Type of ID document uploaded')
    )
    id_document = models.FileField(
        upload_to='kyc_documents/%Y/%m/',
        blank=True,
        null=True,
        help_text=_('ID document for verification (passport, driver license, etc.)')
    )
    id_verified = models.BooleanField(
        default=False,
        help_text=_('ID verification status - verified by admin')
    )
    id_verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('Date when ID was verified')
    )
    id_verification_notes = models.TextField(
        blank=True,
        help_text=_('Admin notes regarding ID verification')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Override save to generate user_id and initialize dual-role system"""
        if not self.user_id:
            while True:
                user_id = str(random.randint(1000, 9999))
                if not User.objects.filter(user_id=user_id).exists():
                    self.user_id = user_id
                    break
        
        # Every user gets BOTH tenant and landlord roles by default
        if not self.roles:
            self.roles = [self.Role.TENANT, self.Role.LANDLORD]
        
        # Ensure both TENANT and LANDLORD are always in roles (unless AGENT or SUPER_ADMIN)
        if self.role not in [self.Role.AGENT, self.Role.SUPER_ADMIN]:
            if self.Role.TENANT not in self.roles:
                self.roles.append(self.Role.TENANT)
            if self.Role.LANDLORD not in self.roles:
                self.roles.append(self.Role.LANDLORD)
        else:
            # Agents and Super Admins only get their specific role
            if not self.roles:
                self.roles = [self.role]
            elif self.role not in self.roles:
                self.roles.append(self.role)
        
        # Set active_role to primary role if not set
        if not self.active_role:
            self.active_role = self.role
        
        # Ensure active_role is valid
        if self.active_role not in self.roles:
            self.active_role = self.role
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def add_role(self, role):
        """Add a new role to user's roles list"""
        if role not in self.roles and role in [r[0] for r in self.Role.choices]:
            self.roles.append(role)
            self.save()
            return True
        return False
    
    def remove_role(self, role):
        """Remove a role from user's roles list (cannot remove primary role)"""
        if role != self.role and role in self.roles:
            self.roles.remove(role)
            if self.active_role == role:
                self.active_role = self.role
            self.save()
            return True
        return False
    
    def switch_role(self, role):
        """Switch to a different active role"""
        if role in self.roles:
            self.active_role = role
            self.save()
            return True
        return False
    
    @property
    def is_multi_role(self):
        """Check if user has dual tenant/landlord roles (always True for regular users)"""
        # Agents and Super Admins are single-role
        if self.role in [self.Role.AGENT, self.Role.SUPER_ADMIN]:
            return False
        # Regular users always have both tenant and landlord roles
        return True
    
    @property
    def available_roles(self):
        """Get list of role choices for this user"""
        return [(r, dict(self.Role.choices).get(r)) for r in self.roles]
    
    @property
    def current_role_display(self):
        """Get display name of currently active role"""
        return dict(self.Role.choices).get(self.active_role, self.get_role_display())
    
    @property
    def is_tenant(self):
        return self.active_role == self.Role.TENANT
    
    @property
    def is_landlord(self):
        return self.active_role == self.Role.LANDLORD
    
    @property
    def is_agent(self):
        return self.active_role == self.Role.AGENT
    
    @property
    def is_super_admin(self):
        return self.active_role == self.Role.SUPER_ADMIN
    
    @property
    def has_tenant_role(self):
        """Check if user has tenant role (regardless of active role)"""
        return self.Role.TENANT in self.roles
    
    @property
    def has_landlord_role(self):
        """Check if user has landlord role (regardless of active role)"""
        return self.Role.LANDLORD in self.roles
    
    @property
    def has_agent_role(self):
        """Check if user has agent role (regardless of active role)"""
        return self.Role.AGENT in self.roles


class EmailVerificationToken(models.Model):
    """
    Email verification tokens for user account activation
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Email Verification Token')
        verbose_name_plural = _('Email Verification Tokens')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token for {self.user.email}"
    
    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()


# ============================================================================
# PROPERTY MODELS
# ============================================================================

class Property(models.Model):
    """
    Property model representing real estate listings
    """
    
    class PropertyType(models.TextChoices):
        APARTMENT = 'APARTMENT', _('Apartment')
        HOUSE = 'HOUSE', _('House')
        VILLA = 'VILLA', _('Villa')
        OFFICE = 'OFFICE', _('Office')
        SHOP = 'SHOP', _('Shop')
        WAREHOUSE = 'WAREHOUSE', _('Warehouse')
        LAND = 'LAND', _('Land')
    
    class PropertyStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Available')
        RENTED = 'RENTED', _('Rented')
        SOLD = 'SOLD', _('Sold')
        UNDER_MAINTENANCE = 'UNDER_MAINTENANCE', _('Under Maintenance')
        PENDING = 'PENDING', _('Pending Approval')
        DRAFT = 'DRAFT', _('Draft')
    
    class ListingType(models.TextChoices):
        RENT = 'RENT', _('For Rent')
        SALE = 'SALE', _('For Sale')
        BOTH = 'BOTH', _('Rent or Sale')
    
    # Basic Information
    title = models.CharField(
        max_length=255,
        help_text=_('Property title/name')
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text=_('URL-friendly identifier')
    )
    description = models.TextField(
        help_text=_('Detailed property description')
    )
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        help_text=_('Type of property')
    )
    listing_type = models.CharField(
        max_length=10,
        choices=ListingType.choices,
        default=ListingType.RENT,
        help_text=_('Listing type (rent/sale)')
    )
    status = models.CharField(
        max_length=20,
        choices=PropertyStatus.choices,
        default=PropertyStatus.DRAFT,
        help_text=_('Current property status')
    )
    
    # Pricing
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Property price or monthly rent')
    )
    currency = models.CharField(
        max_length=3,
        default='NGN',
        help_text=_('Currency code (NGN, USD, EUR, etc.)')
    )
    
    # Location
    address = models.TextField(
        help_text=_('Full street address')
    )
    city = models.CharField(
        max_length=100,
        help_text=_('City name')
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('State/Province')
    )
    country = models.CharField(
        max_length=100,
        default='Nigeria',
        help_text=_('Country name')
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Postal/ZIP code')
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text=_('Latitude for map display')
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text=_('Longitude for map display')
    )
    
    # Property Details
    bedrooms = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(50)],
        help_text=_('Number of bedrooms')
    )
    bathrooms = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        help_text=_('Number of bathrooms (allows 0.5 for half baths)')
    )
    living_area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Living area in square meters')
    )
    total_area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text=_('Total area including outdoor space')
    )
    floors = models.PositiveIntegerField(
        default=1,
        validators=[MaxValueValidator(200)],
        help_text=_('Number of floors')
    )
    year_built = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1800), MaxValueValidator(2100)],
        help_text=_('Year property was built')
    )
    garages = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(20)],
        help_text=_('Number of garage spaces')
    )
    
    # Featured Image
    featured_image = models.ImageField(
        upload_to='properties/%Y/%m/',
        blank=True,
        null=True,
        help_text=_('Main property image')
    )
    
    # Relationships
    landlord = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_properties',
        blank=True,
        null=True,
        help_text=_('Property owner (Landlord) - Assigned by admin/agent')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='uploaded_properties',
        null=True,
        limit_choices_to={'role__in': ['AGENT', 'SUPER_ADMIN']},
        help_text=_('Agent/Admin who uploaded this property')
    )
    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='assigned_properties',
        blank=True,
        null=True,
        limit_choices_to={'role': 'AGENT'},
        help_text=_('Assigned agent (optional)')
    )
    
    # Additional Features
    is_featured = models.BooleanField(
        default=False,
        help_text=_('Mark as featured property')
    )
    views_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times property was viewed')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('Date property was published')
    )
    
    class Meta:
        verbose_name = _('Property')
        verbose_name_plural = _('Properties')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'listing_type']),
            models.Index(fields=['city', 'property_type']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.city}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            counter = 1
            while Property.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)
    
    @property
    def formatted_price(self):
        """Return formatted price with currency"""
        currency_symbols = {
            'NGN': '₦',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
        }
        symbol = currency_symbols.get(self.currency, self.currency)
        return f"{symbol}{self.price:,.2f}"
    
    @property
    def is_available(self):
        """Check if property is available"""
        return self.status == self.PropertyStatus.AVAILABLE
    
    @property
    def full_address(self):
        """Return complete formatted address"""
        parts = [self.address, self.city]
        if self.state:
            parts.append(self.state)
        parts.append(self.country)
        if self.postal_code:
            parts.append(self.postal_code)
        return ", ".join(parts)


class PropertyImage(models.Model):
    """
    Property images for gallery display
    """
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='images',
        help_text=_('Associated property')
    )
    image = models.ImageField(
        upload_to='properties/%Y/%m/gallery/',
        help_text=_('Property image')
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Image caption/description')
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_('Mark as primary/main image for this property')
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_('Display order (lower numbers first)')
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Property Image')
        verbose_name_plural = _('Property Images')
        ordering = ['order', '-uploaded_at']
    
    def __str__(self):
        return f"Image for {self.property.title}"


class PropertyDocument(models.Model):
    """
    Property documents like contracts, certificates, floor plans
    """
    
    class DocumentType(models.TextChoices):
        CONTRACT = 'CONTRACT', _('Contract')
        CERTIFICATE = 'CERTIFICATE', _('Certificate')
        FLOOR_PLAN = 'FLOOR_PLAN', _('Floor Plan')
        INSPECTION = 'INSPECTION', _('Inspection Report')
        OTHER = 'OTHER', _('Other')
    
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='documents',
        help_text=_('Associated property')
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        help_text=_('Type of document')
    )
    file = models.FileField(
        upload_to='properties/%Y/%m/documents/',
        help_text=_('Document file')
    )
    title = models.CharField(
        max_length=255,
        help_text=_('Document title')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Document description')
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        help_text=_('User who uploaded the document')
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Property Document')
        verbose_name_plural = _('Property Documents')
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.title} - {self.property.title}"


class Amenity(models.Model):
    """
    Property amenities/features (pool, gym, parking, etc.)
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Amenity name')
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Icon class or path')
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Amenity category (indoor, outdoor, security, etc.)')
    )
    
    class Meta:
        verbose_name = _('Amenity')
        verbose_name_plural = _('Amenities')
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name


class PropertyAmenity(models.Model):
    """
    Many-to-many relationship between Property and Amenity with additional details
    """
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='property_amenities'
    )
    amenity = models.ForeignKey(
        Amenity,
        on_delete=models.CASCADE,
        related_name='property_amenities'
    )
    details = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Additional details about this amenity')
    )
    
    class Meta:
        verbose_name = _('Property Amenity')
        verbose_name_plural = _('Property Amenities')
        unique_together = ['property', 'amenity']
    
    def __str__(self):
        return f"{self.property.title} - {self.amenity.name}"


class BlogCategory(models.Model):
    """Blog categories for organizing posts"""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Category name')
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        help_text=_('URL-friendly version of the name')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Category description')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Blog Category')
        verbose_name_plural = _('Blog Categories')
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Blog(models.Model):
    """Blog posts for the platform"""
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PUBLISHED = 'PUBLISHED', _('Published')
        ARCHIVED = 'ARCHIVED', _('Archived')
    
    title = models.CharField(
        max_length=255,
        help_text=_('Blog post title')
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text=_('URL-friendly version of the title')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blog_posts',
        help_text=_('Blog post author')
    )
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        help_text=_('Blog category')
    )
    excerpt = models.TextField(
        max_length=500,
        help_text=_('Short excerpt or summary')
    )
    content = RichTextUploadingField(
        help_text=_('Full blog post content')
    )
    featured_image = models.ImageField(
        upload_to='blog_images/',
        blank=True,
        null=True,
        help_text=_('Featured image for the blog post')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text=_('Publication status')
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_('Display on homepage or featured sections')
    )
    views_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of views')
    )
    read_time = models.PositiveIntegerField(
        default=5,
        help_text=_('Estimated reading time in minutes')
    )
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        help_text=_('SEO meta description')
    )
    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Comma-separated tags')
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Publication date and time')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Blog Post')
        verbose_name_plural = _('Blog Posts')
        ordering = ['-published_at', '-created_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    def get_tags_list(self):
        """Return tags as a list"""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]


# ============================================================================
# PAYMENT AND RENTAL MANAGEMENT MODELS
# ============================================================================

class RentalAgreement(models.Model):
    """
    Rental agreement between landlord and tenant for a property
    """
    class AgreementStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ACTIVE = 'ACTIVE', _('Active')
        EXPIRED = 'EXPIRED', _('Expired')
        TERMINATED = 'TERMINATED', _('Terminated')
    
    rental_property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name='rental_agreements',
        help_text=_('Property being rented')
    )
    landlord = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='landlord_agreements',
        help_text=_('Property landlord')
    )
    tenant = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='tenant_agreements',
        limit_choices_to={'role': User.Role.TENANT},
        help_text=_('Tenant renting the property')
    )
    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_agreements',
        limit_choices_to={'role': User.Role.AGENT},
        help_text=_('Managing agent')
    )
    
    # Agreement details
    start_date = models.DateField(help_text=_('Rental start date'))
    end_date = models.DateField(help_text=_('Rental end date'))
    monthly_rent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Yearly Rent'),
        help_text=_('Annual rent amount')
    )
    security_deposit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_('Security deposit amount')
    )
    currency = models.CharField(max_length=3, default='NGN')
    
    # Payment schedule
    rent_due_day = models.PositiveIntegerField(
        default=1,
        help_text=_('Day of month when rent is due (1-31)')
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=AgreementStatus.choices,
        default=AgreementStatus.DRAFT,
        help_text=_('Agreement status')
    )
    notes = models.TextField(blank=True, help_text=_('Additional notes'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Rental Agreement')
        verbose_name_plural = _('Rental Agreements')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rental_property.title} - {self.tenant.get_full_name()} ({self.start_date} to {self.end_date})"
    
    @property
    def is_active(self):
        """Check if agreement is currently active"""
        from django.utils import timezone
        today = timezone.now().date()
        return (
            self.status == self.AgreementStatus.ACTIVE and
            self.start_date <= today <= self.end_date
        )
    
    @property
    def duration_months(self):
        """Calculate rental duration in months"""
        from dateutil.relativedelta import relativedelta
        delta = relativedelta(self.end_date, self.start_date)
        return delta.years * 12 + delta.months


class Invoice(models.Model):
    """
    Invoice for rent payments
    """
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SENT = 'SENT', _('Sent')
        PAID = 'PAID', _('Paid')
        OVERDUE = 'OVERDUE', _('Overdue')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text=_('Unique invoice number')
    )
    rental_agreement = models.ForeignKey(
        RentalAgreement,
        on_delete=models.PROTECT,
        related_name='invoices',
        help_text=_('Associated rental agreement')
    )
    tenant = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='invoices',
        help_text=_('Tenant receiving invoice')
    )
    
    # Invoice details
    issue_date = models.DateField(help_text=_('Invoice issue date'))
    due_date = models.DateField(help_text=_('Payment due date'))
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=_('Invoice amount')
    )
    currency = models.CharField(max_length=3, default='NGN')
    
    # Payment tracking
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        help_text=_('Invoice status')
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_('Amount paid')
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Payment date')
    )
    
    # Description
    description = models.TextField(
        blank=True,
        help_text=_('Invoice description/items')
    )
    notes = models.TextField(blank=True, help_text=_('Additional notes'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.tenant.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number: INV-YYYYMMDD-XXXX
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            last_invoice = Invoice.objects.filter(
                invoice_number__startswith=f'INV-{date_str}'
            ).order_by('-invoice_number').first()
            
            if last_invoice:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.invoice_number = f'INV-{date_str}-{new_num:04d}'
        
        # Auto-update status based on dates and payment
        if self.paid_amount >= self.amount:
            self.status = self.InvoiceStatus.PAID
        elif self.status != self.InvoiceStatus.CANCELLED:
            from django.utils import timezone
            today = timezone.now().date()
            if self.due_date < today and self.status != self.InvoiceStatus.PAID:
                self.status = self.InvoiceStatus.OVERDUE
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        from django.utils import timezone
        return (
            self.status not in [self.InvoiceStatus.PAID, self.InvoiceStatus.CANCELLED] and
            self.due_date < timezone.now().date()
        )
    
    @property
    def balance(self):
        """Calculate remaining balance"""
        return self.amount - self.paid_amount


class Payment(models.Model):
    """
    Payment transaction for invoices
    """
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        CARD = 'CARD', _('Credit/Debit Card')
        CASH = 'CASH', _('Cash')
        MOBILE_MONEY = 'MOBILE_MONEY', _('Mobile Money')
        PAYSTACK = 'PAYSTACK', _('Paystack')
        OTHER = 'OTHER', _('Other')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        SUCCESS = 'SUCCESS', _('Success')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')
    
    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        help_text=_('Unique payment reference')
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments',
        help_text=_('Associated invoice')
    )
    tenant = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='payments',
        help_text=_('Tenant making payment')
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=_('Payment amount')
    )
    currency = models.CharField(max_length=3, default='NGN')
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PAYSTACK,
        help_text=_('Payment method')
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text=_('Payment status')
    )
    
    # Payment gateway details
    gateway_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Payment gateway reference/transaction ID')
    )
    gateway_response = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Payment gateway response data')
    )
    
    # Metadata
    notes = models.TextField(blank=True, help_text=_('Payment notes'))
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When payment was processed')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.payment_reference} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        if not self.payment_reference:
            # Generate payment reference: PAY-YYYYMMDD-XXXX
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            last_payment = Payment.objects.filter(
                payment_reference__startswith=f'PAY-{date_str}'
            ).order_by('-payment_reference').first()
            
            if last_payment:
                last_num = int(last_payment.payment_reference.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.payment_reference = f'PAY-{date_str}-{new_num:04d}'
        
        # Update invoice only on the FIRST transition to SUCCESS (prevent double-counting)
        if self.status == self.PaymentStatus.SUCCESS and self.invoice:
            is_new_success = False
            if self.pk:
                try:
                    previous = Payment.objects.get(pk=self.pk)
                    is_new_success = previous.status != self.PaymentStatus.SUCCESS
                except Payment.DoesNotExist:
                    is_new_success = True
            else:
                is_new_success = True  # Brand-new payment created directly as SUCCESS

            if is_new_success:
                self.invoice.paid_amount += self.amount
                if not self.invoice.paid_at:
                    self.invoice.paid_at = self.processed_at or timezone.now()
                self.invoice.save()
        
        super().save(*args, **kwargs)
    
    @property
    def is_successful(self):
        """Check if payment was successful"""
        return self.status == self.PaymentStatus.SUCCESS


class PaymentReceipt(models.Model):
    """
    Receipt for completed payments
    """
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text=_('Unique receipt number')
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name='receipt',
        help_text=_('Associated payment')
    )
    
    # Receipt details
    issued_date = models.DateTimeField(auto_now_add=True)
    issued_to = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='receipts',
        help_text=_('Tenant receiving receipt')
    )
    
    # PDF storage
    pdf_file = models.FileField(
        upload_to='receipts/%Y/%m/',
        null=True,
        blank=True,
        help_text=_('Generated PDF receipt')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Payment Receipt')
        verbose_name_plural = _('Payment Receipts')
        ordering = ['-issued_date']
    
    def __str__(self):
        return f"Receipt #{self.receipt_number}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate receipt number: REC-YYYYMMDD-XXXX
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            last_receipt = PaymentReceipt.objects.filter(
                receipt_number__startswith=f'REC-{date_str}'
            ).order_by('-receipt_number').first()
            
            if last_receipt:
                last_num = int(last_receipt.receipt_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.receipt_number = f'REC-{date_str}-{new_num:04d}'
        
        super().save(*args, **kwargs)


# ============================================================================
# SITE SETTINGS (SINGLETON)
# ============================================================================

class SiteSettings(models.Model):
    """
    Singleton model for site-wide configuration.
    Only one instance (pk=1) should ever exist.
    """
    contact_number = models.CharField(
        max_length=30,
        blank=True,
        help_text=_('Contact phone number shown on property pages (Super Admin number)')
    )

    class Meta:
        verbose_name = _('Site Settings')
        verbose_name_plural = _('Site Settings')

    def __str__(self):
        return 'Site Settings'

    def save(self, *args, **kwargs):
        self.pk = 1  # Enforce singleton
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ============================================================================
# BROADCAST MESSAGES
# ============================================================================

class BroadcastMessage(models.Model):
    """
    Admin-to-user broadcast messages. Admin selects a recipient category
    and the message is visible to all users in that group.
    """
    class RecipientCategory(models.TextChoices):
        ALL = 'ALL', _('All Users')
        TENANTS = 'TENANTS', _('Tenants')
        LANDLORDS = 'LANDLORDS', _('Landlords')
        AGENTS = 'AGENTS', _('Agents')

    subject = models.CharField(max_length=255)
    body = models.TextField()
    recipient_category = models.CharField(
        max_length=20,
        choices=RecipientCategory.choices,
        default=RecipientCategory.ALL,
    )
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_broadcasts',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Broadcast Message')
        verbose_name_plural = _('Broadcast Messages')

    def __str__(self):
        return f'{self.subject} → {self.get_recipient_category_display()}'
