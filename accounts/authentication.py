from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from .models import Admin

User = get_user_model()

class AdminJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication for Admin users only.
    Validates token has admin claims and user is actually an admin.
    """
    
    def authenticate(self, request):
        # First validate the JWT token
        result = super().authenticate(request)
        if result is None:
            return None
        
        user, token = result
        
        # Check if token has admin-specific claims
        is_admin = token.payload.get('is_admin', False)
        role = token.payload.get('role', '')
        
        # Token must have admin claims
        if not is_admin and role != 'admin':
            raise AuthenticationFailed('Invalid admin token. This endpoint requires admin authentication.')
        
        # User must have admin role
        if not user.is_admin:
            raise AuthenticationFailed('User does not have admin privileges.')
        
        # User must be active
        if not user.is_active or user.status != 'active':
            raise AuthenticationFailed('Admin account is deactivated.')
        
        return (user, token)


class UserJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication for regular Users only.
    Ensures admin tokens cannot access user endpoints.
    """
    
    def authenticate(self, request):
        # First validate the JWT token
        result = super().authenticate(request)
        if result is None:
            return None
        
        user, token = result
        
        # Check if token has admin claims (reject if yes)
        is_admin = token.payload.get('is_admin', False)
        role = token.payload.get('role', '')
        
        # Reject admin tokens
        if is_admin or role == 'admin':
            raise AuthenticationFailed('Admin tokens are not allowed for user endpoints.')
        
        # User must NOT be admin
        if user.is_admin:
            raise AuthenticationFailed('Admin accounts cannot access user endpoints.')
        
        # User must be active
        if not user.is_active or user.status != 'active':
            raise AuthenticationFailed('User account is deactivated.')
        
        return (user, token)