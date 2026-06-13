from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Admin
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .authentication import AdminJWTAuthentication
from .admin_serializers import (
    AdminSignupSerializer, AdminLoginSerializer, 
    AdminProfileSerializer, AdminProfileUpdateSerializer,
    AdminChangePasswordSerializer
)
import random
import string
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()


def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

class AdminForgotPasswordView(APIView):
    """Send OTP to admin's email"""
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({
                'success': False,
                'message': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            admin = Admin.objects.get(email=email)
        except Admin.DoesNotExist:
            # For security, don't reveal if email exists
            return Response({
                'success': True,
                'message': 'If your email is registered, you will receive an OTP'
            }, status=status.HTTP_200_OK)
        
        # Generate OTP
        otp = generate_otp()
        
        # Save OTP to admin
        admin.otp_code = otp
        admin.otp_created_at = timezone.now()
        admin.otp_verified = False
        admin.save()
        
        # Send email
        try:
            subject = 'Admin Password Reset OTP - House Price Predictor'
            message = f"""
            Hello Admin {admin.username},
            
            You requested to reset your admin password.
            
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


class AdminVerifyOTPView(APIView):
    """Verify OTP code for admin"""
    authentication_classes = []
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
            admin = Admin.objects.get(email=email)
        except Admin.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid email'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if OTP exists and not expired
        if not admin.otp_code or admin.otp_code != otp:
            return Response({
                'success': False,
                'message': 'Invalid OTP code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if OTP is expired (10 minutes)
        if admin.otp_created_at:
            expiry_time = admin.otp_created_at + timedelta(minutes=10)
            if timezone.now() > expiry_time:
                return Response({
                    'success': False,
                    'message': 'OTP has expired. Please request a new one.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as verified
        admin.otp_verified = True
        admin.save()
        
        return Response({
            'success': True,
            'message': 'OTP verified successfully'
        }, status=status.HTTP_200_OK)


class AdminResetPasswordView(APIView):
    """Reset admin password after OTP verification"""
    authentication_classes = []
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
            admin = Admin.objects.get(email=email)
        except Admin.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Admin not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if OTP was verified
        if not admin.otp_verified:
            return Response({
                'success': False,
                'message': 'Please verify your OTP first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset password
        admin.set_password(new_password)
        admin.otp_code = None
        admin.otp_created_at = None
        admin.otp_verified = False
        admin.save()
        
        # Also update User model password if exists
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
        except User.DoesNotExist:
            pass
        
        return Response({
            'success': True,
            'message': 'Password reset successfully'
        }, status=status.HTTP_200_OK)

class AdminSignupView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = AdminSignupSerializer(data=request.data)
        
        if serializer.is_valid():
            admin = serializer.save()
            
            is_first_user = User.objects.count() == 0
            
            user, created = User.objects.get_or_create(
                email=admin.email,
                defaults={
                    'username': admin.username,
                    'phone': admin.phone or '',
                    'role': 'admin',
                    'is_staff': True,
                    'is_active': True,
                    'status': 'active',
                }
            )
            
            if not created and user.role != 'admin':
                user.role = 'admin'
                user.is_staff = True
                user.save()
            
            refresh = RefreshToken.for_user(user)
            refresh['is_admin'] = True
            refresh['role'] = 'admin'
            refresh['admin_id'] = admin.admin_id
            
            return Response({
                'success': True,
                'message': 'Admin account created successfully',
                'data': {
                    'admin': AdminProfileSerializer(admin).data,
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh)
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            admin = serializer.validated_data['admin']
            
            try:
                user = User.objects.get(email=admin.email)
                
                if user.role != 'admin':
                    return Response({
                        'success': False,
                        'message': 'Access denied. This portal is for administrators only.'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                if not user.is_active or user.status != 'active':
                    return Response({
                        'success': False,
                        'message': 'Your account has been deactivated.'
                    }, status=status.HTTP_403_FORBIDDEN)
                    
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=admin.email,
                    username=admin.username,
                    password=request.data.get('password'),
                    role='admin',
                    is_staff=True,
                    is_active=True,
                    status='active'
                )
            
            user.update_last_login_info(
                ip_address=request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
            )
            
            refresh = RefreshToken.for_user(user)
            refresh['is_admin'] = True
            refresh['role'] = 'admin'
            refresh['admin_id'] = admin.admin_id
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'data': {
                    'admin': AdminProfileSerializer(admin).data,
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh)
                }
            })
        
        return Response({
            'success': False,
            'message': 'Invalid credentials',
            'errors': serializer.errors
        }, status=status.HTTP_401_UNAUTHORIZED)


class AdminProfileView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        try:
            admin = Admin.objects.get(email=user.email)
        except Admin.DoesNotExist:
            return Response({'success': False, 'message': 'Admin profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT full_name, address, bio, profile_image FROM `admin` WHERE admin_id = %s", [admin.admin_id])
            row = cursor.fetchone()
            if row:
                admin.full_name = row[0] or ''
                admin.address = row[1] or ''
                admin.bio = row[2] or ''
                admin.profile_image = row[3] or ''
        
        serializer = AdminProfileSerializer(admin, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


class AdminProfileUpdateView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def put(self, request):
        user = request.user
        try:
            admin = Admin.objects.get(email=user.email)
        except Admin.DoesNotExist:
            return Response({'success': False, 'message': 'Admin not found'}, status=status.HTTP_404_NOT_FOUND)
        
        changed = False
        
        # Handle text fields
        if request.data.get('username') is not None:
            val = request.data.get('username', '').strip()
            if val and not Admin.objects.filter(username=val).exclude(admin_id=admin.admin_id).exists():
                admin.username = val
                changed = True
        
        if request.data.get('email') is not None:
            val = request.data.get('email', '').strip()
            if val and not Admin.objects.filter(email=val).exclude(admin_id=admin.admin_id).exists():
                admin.email = val
                user.email = val
                user.save()
                changed = True
        
        if request.data.get('phone') is not None:
            admin.phone = request.data.get('phone', '')
            changed = True
        
        # Handle profile image upload
        if 'profile_image' in request.FILES:
            image = request.FILES['profile_image']
            import os
            from django.conf import settings
            
            # Create directory if not exists
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'admin_profiles')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            ext = os.path.splitext(image.name)[1]
            filename = f'admin_{admin.admin_id}_{int(timezone.now().timestamp())}{ext}'
            filepath = os.path.join(upload_dir, filename)
            
            with open(filepath, 'wb+') as destination:
                for chunk in image.chunks():
                    destination.write(chunk)
            
            # Save relative path to database
            from django.db import connection
            relative_path = f'admin_profiles/{filename}'
            with connection.cursor() as cursor:
                cursor.execute("UPDATE `admin` SET `profile_image` = %s WHERE admin_id = %s", [relative_path, admin.admin_id])
            
            changed = True
        
        if changed:
            admin.save()
        
        # Handle extra fields via raw SQL
        extra_fields = {}
        for field in ['full_name', 'address', 'bio']:
            if request.data.get(field) is not None:
                extra_fields[field] = request.data.get(field, '')
        
        if extra_fields:
            from django.db import connection
            set_clause = ', '.join([f"`{k}` = %s" for k in extra_fields.keys()])
            values = list(extra_fields.values())
            values.append(admin.admin_id)
            with connection.cursor() as cursor:
                cursor.execute(f"UPDATE `admin` SET {set_clause} WHERE admin_id = %s", values)
        
        # Return updated profile
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'data': AdminProfileSerializer(admin, context={'request': request}).data
        })
    
class AdminChangePasswordView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        print(f"User email: {user.email}")
        try:
            admin = Admin.objects.get(email=user.email)
            print(f"Admin found: {admin.username}, email: {admin.email}")
            print(f"Admin password check: {admin.check_password('admin123')}")
        except Admin.DoesNotExist:
            return Response({'success': False, 'message': 'Admin not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminChangePasswordSerializer(data=request.data, context={'admin': admin})
        if serializer.is_valid():
            serializer.save(admin)
            user.set_password(request.data.get('new_password'))
            user.save()
            return Response({'success': True, 'message': 'Password changed successfully'})
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class AdminLogoutView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'success': True, 'message': 'Logged out successfully'})
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)