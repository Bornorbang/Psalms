"""
Middleware for role verification and access control
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class RoleVerificationMiddleware:
    """
    Middleware to verify user roles and redirect to appropriate pages
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process the request before view
        if request.user.is_authenticated:
            # Add user role flags to request for easy access in templates
            request.is_tenant = request.user.is_tenant
            request.is_landlord = request.user.is_landlord
            request.is_agent = request.user.is_agent
            request.is_super_admin = request.user.is_super_admin
        
        response = self.get_response(request)
        return response


class EmailVerificationMiddleware:
    """
    Middleware to check email verification for certain actions
    """
    
    # URLs that require email verification
    VERIFICATION_REQUIRED_URLS = [
        '/properties/create/',
        '/dashboard/',
        '/profile/edit/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated and not request.user.email_verified:
            # Check if user is trying to access protected URLs
            for url in self.VERIFICATION_REQUIRED_URLS:
                if request.path.startswith(url):
                    messages.warning(
                        request, 
                        'Please verify your email address to access this feature.'
                    )
                    return redirect('home')
        
        response = self.get_response(request)
        return response


class ProfileCompletionMiddleware:
    """
    Middleware to track profile completion status
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Calculate profile completion percentage
            user = request.user
            total_fields = 6
            completed_fields = 0
            
            if user.first_name:
                completed_fields += 1
            if user.last_name:
                completed_fields += 1
            if user.email:
                completed_fields += 1
            if user.phone_number:
                completed_fields += 1
            if user.profile_picture:
                completed_fields += 1
            if user.email_verified:
                completed_fields += 1
            
            # Add completion percentage to request
            request.profile_completion = int((completed_fields / total_fields) * 100)
            request.profile_is_complete = completed_fields == total_fields
        
        response = self.get_response(request)
        return response
