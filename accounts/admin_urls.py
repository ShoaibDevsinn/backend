from django.urls import path
from .admin_views import (
    AdminSignupView, AdminLoginView, AdminProfileView,
    AdminProfileUpdateView, AdminChangePasswordView, AdminLogoutView
)
from .user_views import (
    DashboardStatsView, UserListView, UserDetailView, CreateUserView,
    UpdateUserView, DeleteUserView, ChangeUserStatusView, ChangeUserRoleView,
    BulkUserActionView
)
from accounts import admin_views

urlpatterns = [
    # Admin Auth
    path('signup', AdminSignupView.as_view(), name='admin-signup'),
    path('login', AdminLoginView.as_view(), name='admin-login'),
    path('profile', AdminProfileView.as_view(), name='admin-profile'),
    path('profile/update', AdminProfileUpdateView.as_view(), name='admin-profile-update'),
    path('change-password', AdminChangePasswordView.as_view(), name='admin-change-password'),
    path('logout', AdminLogoutView.as_view(), name='admin-logout'),
    path('forgot-password/', admin_views.AdminForgotPasswordView.as_view(), name='admin-forgot-password'),
    path('verify-otp/', admin_views.AdminVerifyOTPView.as_view(), name='admin-verify-otp'),
    path('reset-password/', admin_views.AdminResetPasswordView.as_view(), name='admin-reset-password'),
    
    # User Management
    path('users/stats/', DashboardStatsView.as_view(), name='admin-user-stats'),
    path('users/', UserListView.as_view(), name='admin-user-list'),
    path('users/create/', CreateUserView.as_view(), name='admin-user-create'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='admin-user-detail'),
    path('users/update/<int:user_id>/', UpdateUserView.as_view(), name='admin-user-update'),
    path('users/delete/<int:user_id>/', DeleteUserView.as_view(), name='admin-user-delete'),
    path('users/change-status/<int:user_id>/', ChangeUserStatusView.as_view(), name='admin-user-change-status'),
    path('users/change-role/<int:user_id>/', ChangeUserRoleView.as_view(), name='admin-user-change-role'),
    path('users/bulk-action/', BulkUserActionView.as_view(), name='admin-user-bulk-action'),
]