"""
Authorization decorators for role-based access control
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import User


def role_required(*allowed_roles):
    """
    Decorator to restrict access to specific user roles.
    Uses active_role for multi-role support.
    Usage: @role_required('TENANT', 'LANDLORD')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if request.user.active_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('home')
        return wrapped_view
    return decorator


def tenant_required(view_func):
    """Decorator to restrict access to tenants only"""
    return role_required(User.Role.TENANT)(view_func)


def landlord_required(view_func):
    """Decorator to restrict access to landlords only"""
    return role_required(User.Role.LANDLORD)(view_func)


def agent_required(view_func):
    """Decorator to restrict access to agents only"""
    return role_required(User.Role.AGENT)(view_func)


def super_admin_required(view_func):
    """Decorator to restrict access to super admins only"""
    return role_required(User.Role.SUPER_ADMIN)(view_func)


def landlord_or_agent_required(view_func):
    """Decorator for views accessible by landlords and agents"""
    return role_required(User.Role.LANDLORD, User.Role.AGENT)(view_func)


def agent_or_admin_required(view_func):
    """Decorator for views accessible by agents and super admins"""
    return role_required(User.Role.AGENT, User.Role.SUPER_ADMIN)(view_func)


def email_verified_required(view_func):
    """
    Decorator to ensure user has verified their email
    """
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if request.user.email_verified:
            return view_func(request, *args, **kwargs)
        else:
            messages.warning(request, 'Please verify your email address to access this feature.')
            return redirect('home')
    return wrapped_view


def profile_complete_required(view_func):
    """
    Decorator to ensure user has completed their profile
    """
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        user = request.user
        # Check if profile is complete
        required_fields = ['first_name', 'last_name', 'email', 'phone_number']
        is_complete = all(getattr(user, field, None) for field in required_fields)
        
        if is_complete:
            return view_func(request, *args, **kwargs)
        else:
            messages.warning(request, 'Please complete your profile to access this feature.')
            return redirect('profile_edit')
    return wrapped_view


class PermissionChecker:
    """
    Helper class for checking permissions in views
    """
    
    @staticmethod
    def user_can_edit_property(user, property_obj):
        """Check if user can edit a property"""
        if user.is_super_admin:
            return True
        if user.is_landlord and property_obj.landlord == user:
            return True
        if user.is_agent and property_obj.agent == user:
            return True
        return False
    
    @staticmethod
    def user_can_delete_property(user, property_obj):
        """Check if user can delete a property"""
        if user.is_super_admin:
            return True
        if user.is_landlord and property_obj.landlord == user:
            return True
        return False
    
    @staticmethod
    def user_can_view_dashboard(user, dashboard_type):
        """Check if user can view a specific dashboard"""
        dashboard_roles = {
            'tenant': [User.Role.TENANT],
            'landlord': [User.Role.LANDLORD],
            'agent': [User.Role.AGENT],
            'admin': [User.Role.SUPER_ADMIN],
        }
        return user.role in dashboard_roles.get(dashboard_type, [])
    
    @staticmethod
    def user_can_manage_users(user):
        """Check if user can manage other users"""
        return user.is_super_admin or user.is_agent
