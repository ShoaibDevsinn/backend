from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from .serializers import RegisterSerializer, UserSerializer
from .authentication import UserJWTAuthentication

User = get_user_model()

class RegisterView(APIView):
    authentication_classes = []  # No auth needed for registration
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens with user-specific claims
            refresh = RefreshToken.for_user(user)
            refresh['is_admin'] = False
            refresh['role'] = 'user'
            
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'data': {
                    'user': UserSerializer(user).data,
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh)
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    authentication_classes = []  # No auth needed for login
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'success': False,
                'message': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # First, check if this email belongs to an admin
        try:
            user = User.objects.get(email=email)
            if user.role == 'admin' or user.is_admin:
                return Response({
                    'success': False,
                    'message': 'This email belongs to an admin account. Please use the admin login portal.'
                }, status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            pass
        
        # Authenticate user
        user = authenticate(email=email, password=password)
        
        if user:
            # CRITICAL: Double-check the user is not an admin
            if user.role == 'admin' or user.is_admin:
                return Response({
                    'success': False,
                    'message': 'Admin accounts cannot login here. Please use the admin login portal.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if user account is active
            if not user.is_active or user.status != 'active':
                return Response({
                    'success': False,
                    'message': 'Your account has been deactivated. Please contact support.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Update last login info
            user.last_login = timezone.now()
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                user.last_login_ip = x_forwarded_for.split(',')[0]
            else:
                user.last_login_ip = request.META.get('REMOTE_ADDR')
            user.save(update_fields=['last_login', 'last_login_ip'])
            
            # Generate JWT tokens with user-specific claims
            refresh = RefreshToken.for_user(user)
            refresh['is_admin'] = False
            refresh['role'] = 'user'
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'data': {
                    'user': UserSerializer(user).data,
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'role': user.role
                }
            })
        
        return Response({
            'success': False,
            'message': 'Invalid email or password'
        }, status=status.HTTP_401_UNAUTHORIZED)