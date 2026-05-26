from django.urls import path
from .views import (
    # Public views
    PublicLocationListView, PublicLocationDetailView, 
    PublicYearComparisonView, PublicLocationYearRangeView,
    PublicDashboardStatsView,
    # Admin views
    LocationRateListView, LocationRateDetailView, CreateLocationView,
    AddYearView, YearRateView, BulkYearRatesView, DashboardStatsView,
    PriceHistoryLogView, LocationYearRangeView, YearComparisonView,
    ExportDataView, ImportDataView, AreaStatisticsView
)

urlpatterns = [
    # ==========================================
    # PUBLIC ENDPOINTS (No Authentication)
    # ==========================================
    
    # Dashboard stats (public)
    path('public/stats', PublicDashboardStatsView.as_view(), name='public-stats'),
    
    # List all locations (public)
    path('public/locations', PublicLocationListView.as_view(), name='public-locations'),
    
    # Single location details (public)
    path('public/locations/<int:location_id>', PublicLocationDetailView.as_view(), name='public-location-detail'),
    
    # Location years (public)
    path('public/locations/<int:location_id>/years', PublicLocationYearRangeView.as_view(), name='public-location-years'),
    
    # Compare years (public)
    path('public/locations/<int:location_id>/compare-years', PublicYearComparisonView.as_view(), name='public-compare-years'),
    
    # ==========================================
    # ADMIN ENDPOINTS (Authentication Required)
    # ==========================================
    
    # Dashboard & Statistics
    path('admin/dashboard/stats', DashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('admin/dashboard/overview', DashboardStatsView.as_view(), name='admin-dashboard-overview'),
    path('admin/area-statistics', AreaStatisticsView.as_view(), name='admin-area-statistics'),
    
    # Locations CRUD
    path('admin/locations', LocationRateListView.as_view(), name='admin-location-list'),
    path('admin/locations/create', CreateLocationView.as_view(), name='admin-location-create'),
    path('admin/locations/<int:location_id>', LocationRateDetailView.as_view(), name='admin-location-detail'),
    path('admin/locations/<int:location_id>/years', LocationYearRangeView.as_view(), name='admin-location-years'),
    
    # Year Rates Management
    path('admin/locations/<int:location_id>/add-year', AddYearView.as_view(), name='admin-add-year'),
    path('admin/locations/<int:location_id>/year/<int:year>', YearRateView.as_view(), name='admin-year-rate'),
    path('admin/locations/<int:location_id>/bulk-years', BulkYearRatesView.as_view(), name='admin-bulk-years'),
    
    # Year Comparison
    path('admin/locations/<int:location_id>/compare-years', YearComparisonView.as_view(), name='admin-compare-years'),
    
    # History Logs
    path('admin/history', PriceHistoryLogView.as_view(), name='admin-all-history'),
    path('admin/locations/<int:location_id>/history', PriceHistoryLogView.as_view(), name='admin-location-history'),
    
    # Data Import/Export
    path('admin/export', ExportDataView.as_view(), name='admin-export-data'),
    path('admin/import', ImportDataView.as_view(), name='admin-import-data'),
]