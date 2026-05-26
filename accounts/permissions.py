from rest_framework.permissions import BasePermission
from django.contrib.auth import get_user_model

User = get_user_model()

class IsAdminUser(BasePermission):
    """
    Custom permission to only allow users with admin role.
    Works with the unified User model.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has admin role
        return request.user.is_admin
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsRegularUser(BasePermission):
    """
    Custom permission to only allow regular users (not admins).
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # User must not be admin
        return not request.user.is_admin


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission to only allow owners or admins to edit.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions only for admin who owns the object
        if request.user.is_admin and hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False
