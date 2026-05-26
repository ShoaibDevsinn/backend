from django.urls import path
from .views import RegisterView, LoginView
from .user_views import (
    DashboardStatsView, UserListView, UserDetailView, CreateUserView,
    UpdateUserView, DeleteUserView, ChangeUserStatusView, ChangeUserRoleView,
    BulkUserActionView
)
from .authentication import UserJWTAuthentication

urlpatterns = [
    # Auth URLs (no authentication required)
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    
    # User Management URLs (Admin only - use AdminJWTAuthentication)
    path('users/stats/', DashboardStatsView.as_view(), name='user-stats'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/create/', CreateUserView.as_view(), name='user-create'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('users/update/<int:user_id>/', UpdateUserView.as_view(), name='user-update'),
    path('users/delete/<int:user_id>/', DeleteUserView.as_view(), name='user-delete'),
    path('users/change-status/<int:user_id>/', ChangeUserStatusView.as_view(), name='user-change-status'),
    path('users/change-role/<int:user_id>/', ChangeUserRoleView.as_view(), name='user-change-role'),
    path('users/bulk-action/', BulkUserActionView.as_view(), name='user-bulk-action'),
]