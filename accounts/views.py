# accounts/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from .serializers import (
    RegisterSerializer, UserSerializer, ChangePasswordSerializer,
    UpdateEmailSerializer, UpdateUsernameSerializer, ProfileImageSerializer
)
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

User = get_user_model()

def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

class ForgotPasswordView(APIView):
    """Send OTP to user's email"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({
                'success': False,
                'message': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # For security, don't reveal if email exists
            return Response({
                'success': True,
                'message': 'If your email is registered, you will receive an OTP'
            }, status=status.HTTP_200_OK)
        
        # Generate OTP
        otp = generate_otp()
        
        # Save OTP to user
        user.otp_code = otp
        user.otp_created_at = timezone.now()
        user.otp_verified = False
        user.save()
        
        # Send email
        try:
            subject = 'Password Reset OTP - House Price Predictor'
            message = f"""
            Hello {user.username},
            
            You requested to reset your password.
            
            Your OTP code is: {otp}
            
            This code is valid for 10 minutes.
            
            If you did not request this, please ignore this email.
            
            Regards,
            House Price Predictor Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return Response({
                'success': True,
                'message': 'OTP sent to your email'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyOTPView(APIView):
    """Verify OTP code"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        if not email or not otp:
            return Response({
                'success': False,
                'message': 'Email and OTP are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid email'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if OTP exists and not expired
        if not user.otp_code or user.otp_code != otp:
            return Response({
                'success': False,
                'message': 'Invalid OTP code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if OTP is expired (10 minutes)
        if user.otp_created_at:
            expiry_time = user.otp_created_at + timedelta(minutes=10)
            if timezone.now() > expiry_time:
                return Response({
                    'success': False,
                    'message': 'OTP has expired. Please request a new one.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as verified
        user.otp_verified = True
        user.save()
        
        return Response({
            'success': True,
            'message': 'OTP verified successfully'
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """Reset password after OTP verification"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not email or not new_password or not confirm_password:
            return Response({
                'success': False,
                'message': 'Email, new password and confirm password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_password != confirm_password:
            return Response({
                'success': False,
                'message': 'Passwords do not match'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(new_password) < 6:
            return Response({
                'success': False,
                'message': 'Password must be at least 6 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if OTP was verified
        if not user.otp_verified:
            return Response({
                'success': False,
                'message': 'Please verify your OTP first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset password
        user.set_password(new_password)
        user.otp_code = None
        user.otp_created_at = None
        user.otp_verified = False
        user.save()
        
        return Response({
            'success': True,
            'message': 'Password reset successfully'
        }, status=status.HTTP_200_OK)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Add custom claims
            if hasattr(user, 'is_admin'):
                refresh['is_admin'] = user.is_admin
            if hasattr(user, 'role'):
                refresh['role'] = user.role
            else:
                refresh['is_admin'] = False
                refresh['role'] = 'user'
            
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'data': {
                    'user': UserSerializer(user, context={'request': request}).data,
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh)
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'success': False,
                'message': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
            
            # Block admin accounts from user login
            if hasattr(user, 'role') and user.role == 'admin':
                return Response({
                    'success': False,
                    'message': 'Admin accounts cannot login here. Please use admin portal.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check account status
            if hasattr(user, 'status') and user.status != 'active':
                return Response({
                    'success': False,
                    'message': 'Your account is not active. Please contact support.'
                }, status=status.HTTP_403_FORBIDDEN)
                
        except User.DoesNotExist:
            pass
        
        user = authenticate(request, username=email, password=password)
        
        if user:
            # Double-check not admin
            if hasattr(user, 'role') and user.role == 'admin':
                return Response({
                    'success': False,
                    'message': 'Admin accounts cannot login here.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if active
            if not user.is_active:
                return Response({
                    'success': False,
                    'message': 'Your account is inactive.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Update last login info
            user.last_login = timezone.now()
            
            # Update IP if field exists
            if hasattr(user, 'last_login_ip'):
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    user.last_login_ip = x_forwarded_for.split(',')[0]
                else:
                    user.last_login_ip = request.META.get('REMOTE_ADDR')
                user.save(update_fields=['last_login', 'last_login_ip'])
            else:
                user.save(update_fields=['last_login'])
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Add custom claims
            if hasattr(user, 'is_admin'):
                refresh['is_admin'] = user.is_admin
            if hasattr(user, 'role'):
                refresh['role'] = user.role
            else:
                refresh['role'] = 'user'
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'data': {
                    'user': UserSerializer(user, context={'request': request}).data,
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'role': getattr(user, 'role', 'user')
                }
            })
        
        return Response({
            'success': False,
            'message': 'Invalid email or password'
        }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """Logout user by blacklisting refresh token"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response({
                'success': True,
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)


class GetUserInfoView(APIView):
    """Get current authenticated user info"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        user = request.user
        
        # Check old password
        if not user.check_password(old_password):
            return Response({
                'success': False,
                'message': 'Old password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response({
            'success': True,
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    """Refresh access token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response({
                'success': False,
                'message': 'Refresh token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            
            return Response({
                'success': True,
                'access_token': access_token
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response({
                'success': False,
                'message': 'Invalid or expired refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)


# ============================================================
# PROFILE MANAGEMENT VIEWS (NEW)
# ============================================================

class UpdateEmailView(APIView):
    """Update user email - No password verification required"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        new_email = request.data.get('new_email')
        
        if not new_email:
            return Response({
                'success': False,
                'message': 'New email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate email format
        try:
            from django.core.validators import validate_email
            validate_email(new_email)
        except:
            return Response({
                'success': False,
                'message': 'Invalid email format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        # Check if email already exists
        if User.objects.filter(email__iexact=new_email).exclude(user_id=user.user_id).exists():
            return Response({
                'success': False,
                'message': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update email
        old_email = user.email
        user.email = new_email
        user.save()
        
        return Response({
            'success': True,
            'message': 'Email updated successfully',
            'data': {
                'old_email': old_email,
                'new_email': new_email
            }
        }, status=status.HTTP_200_OK)
    

class UpdateUsernameView(APIView):
    """Update username with uniqueness validation"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        serializer = UpdateUsernameSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        new_username = serializer.validated_data['new_username']
        user = request.user
        
        # Check if username already exists - FIX: use user_id instead of id
        if User.objects.filter(username__iexact=new_username).exclude(user_id=user.user_id).exists():
            return Response({
                'success': False,
                'message': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update username
        old_username = user.username
        user.username = new_username
        user.save()
        
        return Response({
            'success': True,
            'message': 'Username updated successfully',
            'data': {
                'old_username': old_username,
                'new_username': new_username
            }
        }, status=status.HTTP_200_OK)


class UpdateProfileImageView(APIView):
    """Upload/Update profile image"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        serializer = ProfileImageSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        profile_image = serializer.validated_data['profile_image']
        
        # Delete old image if exists
        if user.profile_image and user.profile_image.name:
            if default_storage.exists(user.profile_image.name):
                default_storage.delete(user.profile_image.name)
        
        # Save new image
        user.profile_image = profile_image
        user.save()
        
        # Get full URL
        image_url = request.build_absolute_uri(user.profile_image.url) if user.profile_image else None
        
        return Response({
            'success': True,
            'message': 'Profile image updated successfully',
            'data': {
                'profile_image_url': image_url
            }
        }, status=status.HTTP_200_OK)
    
    def delete(self, request):
        """Delete profile image"""
        user = request.user
        
        if user.profile_image and user.profile_image.name:
            if default_storage.exists(user.profile_image.name):
                default_storage.delete(user.profile_image.name)
            user.profile_image = None
            user.save()
            
            return Response({
                'success': True,
                'message': 'Profile image deleted successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'No profile image to delete'
        }, status=status.HTTP_400_BAD_REQUEST)


class GetProfileView(APIView):
    """Get complete user profile with member info"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user, context={'request': request})
        
        # Add member since info
        profile_data = serializer.data
        profile_data['member_since'] = user.created_at.strftime('%B %d, %Y') if hasattr(user, 'created_at') else user.date_joined.strftime('%B %d, %Y')
        profile_data['member_years'] = (timezone.now().date() - (user.created_at.date() if hasattr(user, 'created_at') else user.date_joined.date())).days // 365
        profile_data['full_name'] = getattr(user, 'full_name', user.username)
        profile_data['phone'] = getattr(user, 'phone', '')
        
        return Response({
            'success': True,
            'data': profile_data
        }, status=status.HTTP_200_OK)