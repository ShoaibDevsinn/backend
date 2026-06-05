# accounts/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

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
        is_admin_claim = token.payload.get('is_admin', False)
        role_claim = token.payload.get('role', '')
        
        # Token must have admin claims
        if not is_admin_claim and role_claim != 'admin':
            raise AuthenticationFailed(
                'Invalid admin token. This endpoint requires admin authentication.',
                code='invalid_admin_token'
            )
        
        # Check user role (since User model uses 'role' field, not 'is_admin')
        user_role = getattr(user, 'role', 'user')
        
        # User must have admin role
        if user_role != 'admin':
            raise AuthenticationFailed(
                'User does not have admin privileges.',
                code='not_admin'
            )
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationFailed(
                'Admin account is deactivated.',
                code='account_inactive'
            )
        
        # Check status field if it exists
        if hasattr(user, 'status') and user.status != 'active':
            raise AuthenticationFailed(
                'Admin account is deactivated.',
                code='account_inactive'
            )
        
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
        
        # Check if token has admin claims
        is_admin_claim = token.payload.get('is_admin', False)
        role_claim = token.payload.get('role', '')
        
        # Reject admin tokens
        if is_admin_claim or role_claim == 'admin':
            raise AuthenticationFailed(
                'Admin tokens are not allowed for user endpoints.',
                code='admin_token_rejected'
            )
        
        # Check user role
        user_role = getattr(user, 'role', 'user')
        
        # User must NOT be admin
        if user_role == 'admin':
            raise AuthenticationFailed(
                'Admin accounts cannot access user endpoints.',
                code='admin_access_denied'
            )
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationFailed(
                'User account is deactivated.',
                code='account_inactive'
            )
        
        # Check status field if it exists
        if hasattr(user, 'status') and user.status != 'active':
            raise AuthenticationFailed(
                'User account is deactivated.',
                code='account_inactive'
            )
        
        return (user, token)