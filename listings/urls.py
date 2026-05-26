from django.urls import path
from .views import (
    AdminDashboardStatsView,
    LocationListView,
    AdminAddListingView, AdminGetListingsView, 
    AdminGetListingDetailView, AdminUpdateListingView, 
    AdminDeleteListingView, AdminDeleteListingImageView,
    AdminFilteredListingsView,
    PublicGetListingsView, PublicGetListingDetailView,
    PublicFilteredListingsView,
    FilterOptionsView
)

urlpatterns = [
    # Admin endpoints
    path('admin/add', AdminAddListingView.as_view(), name='admin-add-listing'),
    path('admin/listings', AdminGetListingsView.as_view(), name='admin-get-listings'),
    path('admin/listings/<int:listing_id>', AdminGetListingDetailView.as_view(), name='admin-listing-detail'),
    path('admin/listings/update/<int:listing_id>', AdminUpdateListingView.as_view(), name='admin-update-listing'),
    path('admin/listings/delete/<int:listing_id>', AdminDeleteListingView.as_view(), name='admin-delete-listing'),
    path('admin/delete-image/<int:image_id>', AdminDeleteListingImageView.as_view(), name='admin-delete-image'),
    path('admin/filter', AdminFilteredListingsView.as_view(), name='admin-filter-listings'),
    
    # Public endpoints
    path('locations', LocationListView.as_view(), name='locations'),
    path('listings', PublicGetListingsView.as_view(), name='public-get-listings'),
    path('listings/<int:listing_id>', PublicGetListingDetailView.as_view(), name='public-listing-detail'),
    path('filter', PublicFilteredListingsView.as_view(), name='filter-listings'),
    path('filter-options', FilterOptionsView.as_view(), name='filter-options'),
    path('admin/dashboard-stats', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
]