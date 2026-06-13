from rest_framework.views import APIView
from .authentication import AdminJWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import User
from .user_serializers import (
    UserListSerializer, UserDetailSerializer, CreateUserSerializer,
    UpdateUserSerializer, ChangeUserStatusSerializer, ChangeUserRoleSerializer
)
from .permissions import IsAdminUser

class DashboardStatsView(APIView):
    """Get dashboard statistics"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    
    def get(self, request):
        total_users = User.objects.filter(role='user').count()
        total_admins = User.objects.filter(role='admin').count()
        active_accounts = User.objects.filter(status='active', is_active=True).count()
        inactive_accounts = User.objects.filter(Q(status='inactive') | Q(is_active=False)).count()
        
        # Recent signups (last 30 days)
        from django.utils import timezone
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_signups = User.objects.filter(created_at__gte=thirty_days_ago).count()
        
        return Response({
            'success': True,
            'data': {
                'total_users': total_users,
                'total_admins': total_admins,
                'total_accounts': total_users + total_admins,
                'active_accounts': active_accounts,
                'inactive_accounts': inactive_accounts,
                'recent_signups': recent_signups,
            }
        })


class UserListView(APIView):
    """Get all users with filters"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    
    def get(self, request):
        queryset = User.objects.all()
        
        # Search filter
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(full_name__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Role filter
        role = request.query_params.get('role', 'all')
        if role and role != 'all':
            queryset = queryset.filter(role=role)
        
        # Status filter
        status = request.query_params.get('status', 'all')
        if status and status != 'all':
            queryset = queryset.filter(status=status)
        
        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        if sort_by:
            queryset = queryset.order_by(sort_by)
        
        serializer = UserListSerializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class UserDetailView(APIView):
    """Get single user details"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    def get(self, request, user_id):
        try:
            user = User.objects.get(user_id=user_id)
            serializer = UserDetailSerializer(user)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)


class CreateUserView(APIView):
    """Create new user or admin"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    
    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'success': True,
                'message': f'{user.role.title()} created successfully',
                'data': UserDetailSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UpdateUserView(APIView):
    """Update user details"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    
    def put(self, request, user_id):
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateUserSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'User updated successfully',
                'data': UserDetailSerializer(user).data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DeleteUserView(APIView):
    """Delete user account with all related predictions"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    
    def delete(self, request, user_id):
        # Prevent self-deletion
        if str(request.user.user_id) == str(user_id):
            return Response({
                'success': False,
                'message': 'You cannot delete your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                # Step 1: Delete predictions first (handles foreign key)
                cursor.execute("DELETE FROM prediction WHERE user_id = %s", [user_id])
                
                # Step 2: Delete the user
                cursor.execute("DELETE FROM user WHERE user_id = %s", [user_id])
                
            return Response({
                'success': True,
                'message': 'User deleted successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error deleting user: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChangeUserStatusView(APIView):
    """Activate or deactivate user"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ChangeUserStatusSerializer(data=request.data)
        
        if serializer.is_valid():
            status_value = serializer.validated_data['status']
            user.status = status_value
            user.is_active = (status_value == 'active')
            user.save()
            
            return Response({
                'success': True,
                'message': f'User status changed to {status_value}',
                'data': {
                    'user_id': user.user_id,
                    'status': user.status,
                    'is_active': user.is_active
                }
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ChangeUserRoleView(APIView):
    """Change user role (Admin/User)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    def post(self, request, user_id):
        # Prevent admin from changing their own role
        if request.user.user_id == user_id:
            return Response({
                'success': False,
                'message': 'You cannot change your own role'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ChangeUserRoleSerializer(data=request.data)
        
        if serializer.is_valid():
            new_role = serializer.validated_data['role']
            user.role = new_role
            user.is_staff = (new_role == 'admin')
            user.save()
            
            return Response({
                'success': True,
                'message': f'User role changed to {new_role}',
                'data': {
                    'user_id': user.user_id,
                    'role': user.role,
                    'is_staff': user.is_staff
                }
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class BulkUserActionView(APIView):
    """Bulk actions for users"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [AdminJWTAuthentication]
    
    def post(self, request):
        action = request.data.get('action')
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response({
                'success': False,
                'message': 'No users selected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent self-deletion in bulk
        if action == 'delete' and request.user.user_id in user_ids:
            user_ids.remove(request.user.user_id)
        
        users = User.objects.filter(user_id__in=user_ids)
        
        if action == 'activate':
            users.update(status='active', is_active=True)
            message = f'{users.count()} users activated'
        elif action == 'deactivate':
            users.update(status='inactive', is_active=False)
            message = f'{users.count()} users deactivated'
        elif action == 'delete':
            count = users.count()
            users.delete()
            message = f'{count} users deleted'
        elif action == 'make_admin':
            users.update(role='admin', is_staff=True)
            message = f'{users.count()} users promoted to admin'
        elif action == 'make_user':
            users.update(role='user', is_staff=False)
            message = f'{users.count()} users demoted to user'
        else:
            return Response({
                'success': False,
                'message': 'Invalid action'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': message
        })