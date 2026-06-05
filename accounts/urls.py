from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, 
    GetUserInfoView, ChangePasswordView, RefreshTokenView,
    UpdateEmailView, UpdateUsernameView, UpdateProfileImageView, GetProfileView,
    ForgotPasswordView, VerifyOTPView, ResetPasswordView  # 
)
from .user_views import (
    DashboardStatsView, UserListView, UserDetailView, CreateUserView,
    UpdateUserView, DeleteUserView, ChangeUserStatusView, ChangeUserRoleView,
    BulkUserActionView
)

urlpatterns = [
    # Auth URLs (no authentication required)
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),
    
    # User Auth URLs (authentication required)
    path('logout/', LogoutView.as_view(), name='logout'),
    path('user/', GetUserInfoView.as_view(), name='user-info'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # ============================================================
    # PROFILE MANAGEMENT URLs (User Profile - Authentication required)
    # ============================================================
    path('user/update-email/', UpdateEmailView.as_view(), name='update-email'),
    path('user/update-username/', UpdateUsernameView.as_view(), name='update-username'),
    path('user/update-profile-image/', UpdateProfileImageView.as_view(), name='update-profile-image'),
    path('user/profile/', GetProfileView.as_view(), name='user-profile'),
    
    # ============================================================
    # FORGOT PASSWORD URLs (No authentication required)
    # ============================================================
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    
    # ============================================================
    # User Management URLs (Admin only)
    # ============================================================
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