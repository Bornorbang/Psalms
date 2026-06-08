from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    User, Property, PropertyImage, 
    PropertyDocument, Amenity, PropertyAmenity,
    RentalAgreement, Invoice, Payment, PaymentReceipt,
    SiteSettings, BroadcastMessage
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin with multi-role support
    """
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'display_roles', 'active_role', 'email_verified', 'id_verified', 'is_active', 'date_joined']
    list_filter = ['role', 'active_role', 'email_verified', 'id_verified', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'user_id']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'profile_picture', 'user_id')}),
        (_('Role & Permissions'), {
            'fields': ('role', 'roles', 'active_role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'description': 'Primary role is used for default access. Roles list enables multi-role switching. Active role determines current dashboard view.'
        }),
        (_('Verification'), {'fields': ('email_verified',)}),
        ('KYC/ID Verification', {
            'fields': ('id_type', 'id_document', 'id_verified', 'id_verified_at', 'id_verification_notes')
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    def display_roles(self, obj):
        """Display all roles as badges"""
        if not obj.roles:
            return format_html('<span style="color: #999;">No roles</span>')
        
        role_colors = {
            'TENANT': '#3B82F6',
            'LANDLORD': '#10B981',
            'AGENT': '#F59E0B',
            'SUPER_ADMIN': '#EF4444'
        }
        
        badges = []
        for role in obj.roles:
            color = role_colors.get(role, '#6B7280')
            role_name = dict(User.Role.choices).get(role, role)
            badges.append(
                f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 4px;">{role_name}</span>'
            )
        return format_html(''.join(badges))
    display_roles.short_description = 'All Roles'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Super admins can see everyone
        if request.user.is_superuser:
            return qs
        # Regular staff can only see non-super-admin users
        return qs.exclude(role=User.Role.SUPER_ADMIN)


# ============================================================================
# PROPERTY ADMIN
# ============================================================================

class PropertyImageInline(admin.TabularInline):
    """Inline admin for property images"""
    model = PropertyImage
    extra = 1
    fields = ['image', 'caption', 'order']
    ordering = ['order']


class PropertyDocumentInline(admin.TabularInline):
    """Inline admin for property documents"""
    model = PropertyDocument
    extra = 0
    fields = ['document_type', 'title', 'file', 'uploaded_by']
    readonly_fields = ['uploaded_by']


class PropertyAmenityInline(admin.TabularInline):
    """Inline admin for property amenities"""
    model = PropertyAmenity
    extra = 1
    fields = ['amenity', 'details']
    autocomplete_fields = ['amenity']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    """
    Property admin with inline images, documents, and amenities
    """
    list_display = [
        'title', 'property_type', 'listing_type', 'formatted_price_display', 
        'city', 'status', 'landlord', 'agent', 'is_featured', 'created_at'
    ]
    list_filter = [
        'property_type', 'listing_type', 'status', 'is_featured', 
        'city', 'created_at', 'updated_at'
    ]
    search_fields = ['title', 'description', 'address', 'city', 'landlord__username', 'agent__username']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    autocomplete_fields = ['landlord', 'agent']
    
    def get_readonly_fields(self, request, obj=None):
        """Add formatted_price_display only when editing existing property"""
        if obj:  # Editing existing property
            return list(self.readonly_fields) + ['formatted_price_display']
        return self.readonly_fields
    
    def get_fieldsets(self, request, obj=None):
        """Modify fieldsets based on whether adding or editing"""
        fieldsets = super().get_fieldsets(request, obj)
        # If editing existing property, add formatted_price_display to Pricing section
        if obj:
            fieldsets = list(fieldsets)
            for i, (name, options) in enumerate(fieldsets):
                if name == _('Pricing'):
                    fieldsets[i] = (name, {
                        'fields': ('price', 'currency', 'formatted_price_display')
                    })
            return tuple(fieldsets)
        return fieldsets
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'slug', 'description', 'property_type', 'listing_type', 'status')
        }),
        (_('Pricing'), {
            'fields': ('price', 'currency')
        }),
        (_('Location'), {
            'fields': ('address', 'city', 'state', 'country', 'postal_code', 'latitude', 'longitude')
        }),
        (_('Property Details'), {
            'fields': ('bedrooms', 'bathrooms', 'living_area', 'total_area', 'floors', 'year_built', 'garages')
        }),
        (_('Media'), {
            'fields': ('featured_image',)
        }),
        (_('Ownership'), {
            'fields': ('landlord', 'agent')
        }),
        (_('Features'), {
            'fields': ('is_featured', 'views_count')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PropertyImageInline, PropertyDocumentInline, PropertyAmenityInline]
    
    actions = ['mark_as_available', 'mark_as_rented', 'mark_as_featured', 'unmark_as_featured']
    
    def formatted_price_display(self, obj):
        """Display formatted price in admin"""
        if obj and obj.price is not None:
            return obj.formatted_price
        return '-'
    formatted_price_display.short_description = 'Price'
    
    def mark_as_available(self, request, queryset):
        """Bulk action to mark properties as available"""
        updated = queryset.update(status=Property.PropertyStatus.AVAILABLE)
        self.message_user(request, f'{updated} properties marked as available.')
    mark_as_available.short_description = 'Mark selected as Available'
    
    def mark_as_rented(self, request, queryset):
        """Bulk action to mark properties as rented"""
        updated = queryset.update(status=Property.PropertyStatus.RENTED)
        self.message_user(request, f'{updated} properties marked as rented.')
    mark_as_rented.short_description = 'Mark selected as Rented'
    
    def mark_as_featured(self, request, queryset):
        """Bulk action to mark properties as featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} properties marked as featured.')
    mark_as_featured.short_description = 'Mark as Featured'
    
    def unmark_as_featured(self, request, queryset):
        """Bulk action to unmark properties as featured"""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} properties unmarked as featured.')
    unmark_as_featured.short_description = 'Unmark as Featured'


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    """Property Image admin"""
    list_display = ['property', 'caption', 'order', 'image_preview', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['property__title', 'caption']
    ordering = ['property', 'order', '-uploaded_at']
    
    def image_preview(self, obj):
        """Display image thumbnail in admin"""
        if obj.image:
            return format_html('<img src="{}" width="100" height="75" style="object-fit: cover;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    """Property Document admin"""
    list_display = ['title', 'property', 'document_type', 'uploaded_by', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['title', 'property__title', 'description']
    readonly_fields = ['uploaded_by', 'uploaded_at']
    ordering = ['-uploaded_at']


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    """Amenity admin"""
    list_display = ['name', 'category', 'icon']
    list_filter = ['category']
    search_fields = ['name', 'category']
    ordering = ['category', 'name']


@admin.register(PropertyAmenity)
class PropertyAmenityAdmin(admin.ModelAdmin):
    """Property Amenity relationship admin"""
    list_display = ['property', 'amenity', 'details']
    list_filter = ['amenity__category']
    search_fields = ['property__title', 'amenity__name']
    autocomplete_fields = ['property', 'amenity']


# ============================================================================
# PAYMENT AND RENTAL MANAGEMENT ADMIN
# ============================================================================

@admin.register(RentalAgreement)
class RentalAgreementAdmin(admin.ModelAdmin):
    """Rental Agreement admin"""
    list_display = ['id', 'rental_property', 'tenant', 'landlord', 'start_date', 'end_date', 'monthly_rent', 'status', 'created_at']
    list_filter = ['status', 'start_date', 'end_date', 'created_at']
    search_fields = ['rental_property__title', 'tenant__username', 'tenant__email', 'landlord__username', 'landlord__email']
    date_hierarchy = 'start_date'
    raw_id_fields = ['rental_property', 'tenant', 'landlord', 'agent']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Property & Parties', {
            'fields': ('rental_property', 'landlord', 'tenant', 'agent')
        }),
        ('Agreement Terms', {
            'fields': ('start_date', 'end_date', 'monthly_rent', 'security_deposit', 'currency')
        }),
        ('Status', {
            'fields': ('status', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Invoice admin"""
    list_display = ['invoice_number', 'tenant', 'rental_agreement', 'amount', 'due_date', 'status', 'paid_amount', 'created_at']
    list_filter = ['status', 'issue_date', 'due_date', 'created_at']
    search_fields = ['invoice_number', 'tenant__username', 'tenant__email', 'rental_agreement__rental_property__title']
    date_hierarchy = 'issue_date'
    raw_id_fields = ['rental_agreement', 'tenant']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Invoice Details', {
            'fields': ('invoice_number', 'rental_agreement', 'tenant')
        }),
        ('Amounts & Dates', {
            'fields': ('amount', 'currency', 'issue_date', 'due_date')
        }),
        ('Payment Tracking', {
            'fields': ('status', 'paid_amount', 'paid_at')
        }),
        ('Description', {
            'fields': ('description', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Payment admin"""
    list_display = ['payment_reference', 'tenant', 'invoice', 'amount', 'payment_method', 'status', 'processed_at', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at', 'processed_at']
    search_fields = ['payment_reference', 'tenant__username', 'tenant__email', 'invoice__invoice_number', 'gateway_reference']
    date_hierarchy = 'created_at'
    raw_id_fields = ['invoice', 'tenant']
    readonly_fields = ['payment_reference', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Payment Details', {
            'fields': ('payment_reference', 'invoice', 'tenant')
        }),
        ('Amount & Method', {
            'fields': ('amount', 'currency', 'payment_method')
        }),
        ('Status & Processing', {
            'fields': ('status', 'processed_at')
        }),
        ('Gateway Info', {
            'fields': ('gateway_reference', 'gateway_response'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    """Payment Receipt admin"""
    list_display = ['receipt_number', 'payment', 'issued_to', 'issued_date', 'pdf_file']
    list_filter = ['issued_date']
    search_fields = ['receipt_number', 'payment__payment_reference', 'issued_to__username', 'issued_to__email']
    date_hierarchy = 'issued_date'
    raw_id_fields = ['payment', 'issued_to']
    readonly_fields = ['receipt_number', 'created_at']
    
    fieldsets = (
        ('Receipt Details', {
            'fields': ('receipt_number', 'payment', 'issued_to')
        }),
        ('PDF', {
            'fields': ('pdf_file',)
        }),
        ('Metadata', {
            'fields': ('issued_date', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin for site-wide settings"""
    fieldsets = (
        ('Contact Information', {
            'fields': ('contact_number',),
            'description': 'This number will be shown as the "Call" button on all property detail pages.'
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'recipient_category', 'sent_by', 'created_at']
    list_filter = ['recipient_category', 'created_at']
    search_fields = ['subject', 'body']
    readonly_fields = ['sent_by', 'created_at']

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.sent_by = request.user
        super().save_model(request, obj, form, change)

