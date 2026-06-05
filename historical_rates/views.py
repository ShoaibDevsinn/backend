from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import models, transaction
from django.db.models import Q, Min, Max, Avg
from django.http import HttpResponse
from .models import LocationRate, HistoricalYearRate, PriceHistoryLog, MAX_PRICE
from .serializers import (
    LocationRateSerializer, LocationRateListSerializer, 
    HistoricalYearRateSerializer, CreateLocationSerializer,
    AddYearSerializer, BulkYearRateUpdateSerializer, 
    PriceHistoryLogSerializer, YearComparisonSerializer
)
from accounts.permissions import IsAdminUser
from decimal import Decimal, InvalidOperation
import csv
import io
from datetime import datetime


# ============================================================
# PUBLIC VIEWS - No Authentication Required
# ============================================================

class PublicLocationListView(APIView):
    """
    Public endpoint - Anyone can view locations and rates
    No authentication required
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def get(self, request):
        try:
            locations = LocationRate.objects.prefetch_related('years').all()
            
            # Search functionality
            search = request.query_params.get('search', '')
            if search:
                locations = locations.filter(
                    Q(location_name__icontains=search) |
                    Q(area_name__icontains=search) |
                    Q(city__icontains=search)
                )
            
            # Area filter
            area = request.query_params.get('area', '')
            if area and area != 'All':
                locations = locations.filter(area_name=area)
            
            # City filter
            city = request.query_params.get('city', '')
            if city and city != 'All':
                locations = locations.filter(city=city)
            
            # Year filter - show locations that have data for specific year
            year = request.query_params.get('year', '')
            if year:
                try:
                    year = int(year)
                    locations = locations.filter(years__year=year).distinct()
                except ValueError:
                    pass
            
            # Sorting
            sort_by = request.query_params.get('sort_by', 'location_name')
            sort_order = request.query_params.get('sort_order', 'asc')
            
            valid_sort_fields = ['location_name', 'area_name', 'city', 'created_at']
            if sort_by in valid_sort_fields:
                order_prefix = '-' if sort_order == 'desc' else ''
                locations = locations.order_by(f'{order_prefix}{sort_by}')
            
            # Pagination
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            total_count = locations.count()
            start = (page - 1) * page_size
            end = start + page_size
            
            locations_page = locations[start:end]
            serializer = LocationRateListSerializer(locations_page, many=True)
            
            # Get all unique areas and cities for filter dropdowns
            all_areas = list(LocationRate.objects.values_list('area_name', flat=True).distinct().order_by('area_name'))
            all_cities = list(LocationRate.objects.values_list('city', flat=True).distinct().order_by('city'))
            all_years = list(HistoricalYearRate.objects.values_list('year', flat=True).distinct().order_by('-year'))
            
            return Response({
                'success': True,
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'data': serializer.data,
                'areas': all_areas,
                'cities': all_cities,
                'available_years': all_years
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error fetching locations: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicLocationDetailView(APIView):
    """
    Public endpoint - View single location with all historical data
    No authentication required
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def get(self, request, location_id):
        try:
            location = LocationRate.objects.prefetch_related('years').get(location_rate_id=location_id)
            serializer = LocationRateSerializer(location)
            
            # Calculate additional statistics
            years_data = location.years.all()
            stats = self._calculate_location_stats(years_data)
            
            return Response({
                'success': True,
                'data': serializer.data,
                'statistics': stats
            })
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error fetching location details: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calculate_location_stats(self, years_data):
        """Calculate statistical data for a location"""
        if not years_data:
            return None
        
        stats = {
            'total_years': years_data.count(),
            'year_range': {
                'min': years_data.order_by('year').first().year,
                'max': years_data.order_by('-year').first().year
            }
        }
        
        # Calculate average prices
        for plot_type, field_name in [
            ('5_marla', 'price_5_marla'),
            ('10_marla', 'price_10_marla'),
            ('1_kanal', 'price_1_kanal'),
            ('2_kanal', 'price_2_kanal')
        ]:
            values = [getattr(y, field_name) for y in years_data if getattr(y, field_name)]
            if values:
                stats[f'{plot_type}_avg'] = str(round(sum(values) / len(values), 2))
                stats[f'{plot_type}_min'] = str(min(values))
                stats[f'{plot_type}_max'] = str(max(values))
        
        # Calculate overall growth
        first_year = years_data.order_by('year').first()
        last_year = years_data.order_by('-year').first()
        
        if first_year and last_year and first_year != last_year:
            stats['overall_growth'] = {}
            for plot_type, field_name in [
                ('5_marla', 'price_5_marla'),
                ('10_marla', 'price_10_marla'),
                ('1_kanal', 'price_1_kanal'),
                ('2_kanal', 'price_2_kanal')
            ]:
                first_price = getattr(first_year, field_name)
                last_price = getattr(last_year, field_name)
                
                if first_price and last_price and first_price > 0:
                    total_growth = ((last_price - first_price) / first_price * 100)
                    years_diff = last_year.year - first_year.year
                    # Convert Decimal to float for exponentiation
                    cagr = (float(last_price / first_price) ** (1/years_diff) - 1) * 100 if years_diff > 0 else 0
                    
                    stats['overall_growth'][plot_type] = {
                        'total_growth_percent': round(float(total_growth), 2),
                        'cagr_percent': round(float(cagr), 2),
                        'first_price': str(first_price),
                        'last_price': str(last_price),
                        'absolute_change': str(last_price - first_price)
                    }
        
        return stats


class PublicYearComparisonView(APIView):
    """
    Public endpoint - Compare prices between two years
    No authentication required
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def get(self, request, location_id):
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        year1 = request.query_params.get('year1')
        year2 = request.query_params.get('year2')
        
        if not year1 or not year2:
            return Response({
                'success': False,
                'message': 'Both year1 and year2 are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year1 = int(year1)
            year2 = int(year2)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid year format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data_year1 = HistoricalYearRate.objects.get(location=location, year=year1)
            data_year2 = HistoricalYearRate.objects.get(location=location, year=year2)
        except HistoricalYearRate.DoesNotExist as e:
            return Response({
                'success': False,
                'message': f'Year data not found: {str(e)}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        comparison = {
            'location_name': location.location_name,
            'area_name': location.area_name,
            'city': location.city,
            'year1': year1,
            'year2': year2,
            'plots': {}
        }
        
        plot_types = [
            ('5_marla', 'price_5_marla', 'per_marla_rate_5', 'growth_percentage_5'),
            ('10_marla', 'price_10_marla', 'per_marla_rate_10', 'growth_percentage_10'),
            ('1_kanal', 'price_1_kanal', 'per_marla_rate_1k', 'growth_percentage_1k'),
            ('2_kanal', 'price_2_kanal', 'per_marla_rate_2k', 'growth_percentage_2k'),
        ]
        
        for plot_type, price_field, marla_field, growth_field in plot_types:
            price1 = getattr(data_year1, price_field)
            price2 = getattr(data_year2, price_field)
            
            if price1 and price2:
                change = price2 - price1
                change_percent = (change / price1 * 100) if price1 > 0 else 0
                
                comparison['plots'][plot_type] = {
                    f'price_{year1}': str(price1),
                    f'price_{year2}': str(price2),
                    f'per_marla_{year1}': str(getattr(data_year1, marla_field)) if getattr(data_year1, marla_field) else None,
                    f'per_marla_{year2}': str(getattr(data_year2, marla_field)) if getattr(data_year2, marla_field) else None,
                    'absolute_change': str(change),
                    'percentage_change': round(float(change_percent), 2),
                    'trend': 'up' if change > 0 else 'down' if change < 0 else 'stable'
                }
            else:
                comparison['plots'][plot_type] = {
                    f'price_{year1}': str(price1) if price1 else None,
                    f'price_{year2}': str(price2) if price2 else None,
                    'absolute_change': None,
                    'percentage_change': None,
                    'trend': 'insufficient_data'
                }
        
        return Response({
            'success': True,
            'data': comparison
        })


class PublicLocationYearRangeView(APIView):
    """
    Public endpoint - Get available years for a location
    No authentication required
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def get(self, request, location_id):
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
            years = list(location.years.values_list('year', flat=True).order_by('-year'))
            
            # Get year statistics
            year_stats = {}
            for y in years:
                year_data = location.years.filter(year=y).first()
                if year_data:
                    year_stats[str(y)] = {
                        'has_5_marla': bool(year_data.price_5_marla),
                        'has_10_marla': bool(year_data.price_10_marla),
                        'has_1_kanal': bool(year_data.price_1_kanal),
                        'has_2_kanal': bool(year_data.price_2_kanal),
                    }
            
            return Response({
                'success': True,
                'data': {
                    'location_id': location.location_rate_id,
                    'location_name': location.location_name,
                    'area_name': location.area_name,
                    'city': location.city,
                    'years': years,
                    'year_count': len(years),
                    'year_range': {
                        'min': min(years) if years else None,
                        'max': max(years) if years else None
                    },
                    'year_statistics': year_stats
                }
            })
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)


class PublicDashboardStatsView(APIView):
    """
    Public dashboard statistics
    No authentication required
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def get(self, request):
        try:
            total_locations = LocationRate.objects.count()
            total_records = HistoricalYearRate.objects.count()
            locations_with_data = LocationRate.objects.filter(years__isnull=False).distinct().count()
            
            # Year statistics
            all_years = list(HistoricalYearRate.objects.values_list('year', flat=True).distinct().order_by('year'))
            
            # Area statistics
            areas = list(LocationRate.objects.values_list('area_name', flat=True).distinct())
            cities = list(LocationRate.objects.values_list('city', flat=True).distinct())
            
            # Price statistics
            price_stats = HistoricalYearRate.objects.aggregate(
                avg_price_5_marla=Avg('price_5_marla'),
                avg_price_10_marla=Avg('price_10_marla'),
                avg_price_1_kanal=Avg('price_1_kanal'),
                avg_price_2_kanal=Avg('price_2_kanal'),
                max_price_5_marla=Max('price_5_marla'),
                max_price_10_marla=Max('price_10_marla'),
                max_price_1_kanal=Max('price_1_kanal'),
                max_price_2_kanal=Max('price_2_kanal'),
            )
            
            # Convert Decimal to string for JSON serialization
            for key, value in price_stats.items():
                if value is not None:
                    price_stats[key] = str(value)
            
            return Response({
                'success': True,
                'data': {
                    'total_locations': total_locations,
                    'total_records': total_records,
                    'locations_with_data': locations_with_data,
                    'year_range': {
                        'min': min(all_years) if all_years else None,
                        'max': max(all_years) if all_years else None,
                        'all_years': all_years
                    },
                    'areas': areas,
                    'cities': cities,
                    'area_count': len(areas),
                    'city_count': len(cities),
                    'price_statistics': price_stats,
                    'last_updated': datetime.now().isoformat()
                }
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error fetching stats: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# ADMIN VIEWS - Authentication Required
# ============================================================

class LocationRateListView(APIView):
    """Get all locations with search and filter (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            locations = LocationRate.objects.prefetch_related('years').all()
            
            # Search functionality
            search = request.query_params.get('search', '')
            if search:
                locations = locations.filter(
                    Q(location_name__icontains=search) |
                    Q(area_name__icontains=search) |
                    Q(city__icontains=search)
                )
            
            # Area filter
            area = request.query_params.get('area', '')
            if area and area != 'All':
                locations = locations.filter(area_name=area)
            
            # City filter
            city = request.query_params.get('city', '')
            if city and city != 'All':
                locations = locations.filter(city=city)
            
            # Year filter
            year = request.query_params.get('year', '')
            if year:
                try:
                    year = int(year)
                    locations = locations.filter(years__year=year).distinct()
                except ValueError:
                    pass
            
            # Sorting
            sort_by = request.query_params.get('sort_by', 'location_name')
            sort_order = request.query_params.get('sort_order', 'asc')
            
            valid_sort_fields = ['location_name', 'area_name', 'city', 'created_at']
            if sort_by in valid_sort_fields:
                order_prefix = '-' if sort_order == 'desc' else ''
                locations = locations.order_by(f'{order_prefix}{sort_by}')
            
            # Pagination
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            total_count = locations.count()
            start = (page - 1) * page_size
            end = start + page_size
            
            locations_page = locations[start:end]
            serializer = LocationRateListSerializer(locations_page, many=True)
            
            all_areas = list(LocationRate.objects.values_list('area_name', flat=True).distinct().order_by('area_name'))
            all_cities = list(LocationRate.objects.values_list('city', flat=True).distinct().order_by('city'))
            all_years = list(HistoricalYearRate.objects.values_list('year', flat=True).distinct().order_by('-year'))
            
            return Response({
                'success': True,
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'data': serializer.data,
                'areas': all_areas,
                'cities': all_cities,
                'available_years': all_years
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LocationRateDetailView(APIView):
    """Get/Update/Delete single location (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, location_id):
        try:
            location = LocationRate.objects.prefetch_related('years').get(location_rate_id=location_id)
            serializer = LocationRateSerializer(location)
            
            years_data = location.years.all()
            stats = self._calculate_location_stats(years_data)
            
            return Response({
                'success': True,
                'data': serializer.data,
                'statistics': stats
            })
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, location_id):
        """Update location details"""
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        old_name = location.location_name
        serializer = LocationRateSerializer(location, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Log the update
            PriceHistoryLog.objects.create(
                location=location,
                location_name=location.location_name,
                action='location_updated',
                details=f'Location updated from "{old_name}" to "{location.location_name}"',
                changed_by=request.user
            )
            
            return Response({
                'success': True,
                'message': 'Location updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, location_id):
        """Delete a location and all its year records"""
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
            location_name = location.location_name
            location_area = location.area_name
            
            # Log before deleting
            PriceHistoryLog.objects.create(
                location=location,
                location_name=location_name,
                action='location_deleted',
                details=f'Location "{location_name}" ({location_area}) permanently deleted with all year records',
                changed_by=request.user
            )
            
            location.delete()
            
            return Response({
                'success': True,
                'message': f'Location "{location_name}" deleted successfully'
            })
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _calculate_location_stats(self, years_data):
        """Calculate statistical data for a location"""
        if not years_data:
            return None
        
        stats = {
            'total_years': years_data.count(),
            'year_range': {
                'min': years_data.order_by('year').first().year,
                'max': years_data.order_by('-year').first().year
            }
        }
        
        for plot_type, field_name in [
            ('5_marla', 'price_5_marla'),
            ('10_marla', 'price_10_marla'),
            ('1_kanal', 'price_1_kanal'),
            ('2_kanal', 'price_2_kanal')
        ]:
            values = [getattr(y, field_name) for y in years_data if getattr(y, field_name)]
            if values:
                stats[f'{plot_type}_avg'] = str(round(sum(values) / len(values), 2))
                stats[f'{plot_type}_min'] = str(min(values))
                stats[f'{plot_type}_max'] = str(max(values))
        
        first_year = years_data.order_by('year').first()
        last_year = years_data.order_by('-year').first()
        
        if first_year and last_year and first_year != last_year:
            stats['overall_growth'] = {}
            for plot_type, field_name in [
                ('5_marla', 'price_5_marla'),
                ('10_marla', 'price_10_marla'),
                ('1_kanal', 'price_1_kanal'),
                ('2_kanal', 'price_2_kanal')
            ]:
                first_price = getattr(first_year, field_name)
                last_price = getattr(last_year, field_name)
                
                if first_price and last_price and first_price > 0:
                    total_growth = ((last_price - first_price) / first_price * 100)
                    years_diff = last_year.year - first_year.year
                   # Convert Decimal to float for exponentiation
                    cagr = (float(last_price / first_price) ** (1/years_diff) - 1) * 100 if years_diff > 0 else 0
                    
                    stats['overall_growth'][plot_type] = {
                        'total_growth_percent': round(float(total_growth), 2),
                        'cagr_percent': round(float(cagr), 2),
                        'first_price': str(first_price),
                        'last_price': str(last_price),
                        'absolute_change': str(last_price - first_price)
                    }
        
        return stats


class CreateLocationView(APIView):
    """Create new location with initial year data (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        serializer = CreateLocationSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            with transaction.atomic():
                location = serializer.save()
                
                # Log creation
                PriceHistoryLog.objects.create(
                    location=location,
                    location_name=location.location_name,
                    action='location_added',
                    year=request.data.get('initial_year'),
                    details=f'New location "{location.location_name}" created with {request.data.get("initial_year")} prices',
                    changed_by=request.user
                )
            
            return Response({
                'success': True,
                'message': 'Location created successfully',
                'data': LocationRateSerializer(location).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AddYearView(APIView):
    """Add a new year to existing location (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request, location_id):
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate year
        year = request.data.get('year')
        if not year:
            return Response({
                'success': False,
                'message': 'Year is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'message': 'Year must be a valid number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if year < 2000 or year > 2100:
            return Response({
                'success': False,
                'message': 'Year must be between 2000 and 2100'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if year already exists
        if HistoricalYearRate.objects.filter(location=location, year=year).exists():
            return Response({
                'success': False,
                'message': f'Year {year} already exists for this location'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate prices
        price_fields = ['price_5_marla', 'price_10_marla', 'price_1_kanal', 'price_2_kanal']
        for field in price_fields:
            value = request.data.get(field)
            if value:
                try:
                    decimal_value = Decimal(str(value))
                    if decimal_value > MAX_PRICE:
                        return Response({
                            'success': False,
                            'message': f'{field} cannot exceed 10 Crore (₹{MAX_PRICE:,.2f})'
                        }, status=status.HTTP_400_BAD_REQUEST)
                except (InvalidOperation, ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': f'Invalid value for {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year_rate = HistoricalYearRate(
                location=location,
                year=year,
                updated_by=request.user
            )
            
            # Safe decimal conversion helper
            def safe_decimal(value, default=None):
                try:
                    if value is None or value == '' or value == 'null':
                        return default
                    return Decimal(str(value))
                except (InvalidOperation, ValueError, TypeError):
                    return default
            
            year_rate.price_5_marla = safe_decimal(request.data.get('price_5_marla'), Decimal('0'))
            year_rate.price_10_marla = safe_decimal(request.data.get('price_10_marla'), Decimal('0'))
            year_rate.price_1_kanal = safe_decimal(request.data.get('price_1_kanal'), Decimal('0'))
            year_rate.price_2_kanal = safe_decimal(request.data.get('price_2_kanal'), Decimal('0'))
            
            year_rate.save()
            
            # Log the action
            PriceHistoryLog.objects.create(
                location=location,
                location_name=location.location_name,
                action='year_added',
                year=year,
                details=f'Added historical {year} data for {location.location_name}',
                changed_by=request.user
            )
            
            location_serializer = LocationRateSerializer(location)
            
            return Response({
                'success': True,
                'message': f'Year {year} added successfully',
                'data': {
                    'year_rate': HistoricalYearRateSerializer(year_rate).data,
                    'location': location_serializer.data
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error saving year data: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class YearRateView(APIView):
    """CRUD operations for specific year rates (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, location_id, year):
        try:
            year_rate = HistoricalYearRate.objects.get(location_id=location_id, year=year)
            serializer = HistoricalYearRateSerializer(year_rate)
            
            # Get comparison with previous year
            comparison = self._get_year_comparison(location_id, year)
            
            return Response({
                'success': True,
                'data': serializer.data,
                'comparison': comparison
            })
        except HistoricalYearRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Year data not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, location_id, year):
        """Update specific year prices"""
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate prices
        price_fields = ['price_5_marla', 'price_10_marla', 'price_1_kanal', 'price_2_kanal']
        for field in price_fields:
            value = request.data.get(field)
            if value is not None:
                try:
                    decimal_value = Decimal(str(value))
                    if decimal_value > MAX_PRICE:
                        return Response({
                            'success': False,
                            'message': f'{field} cannot exceed 10 Crore (₹{MAX_PRICE:,.2f})'
                        }, status=status.HTTP_400_BAD_REQUEST)
                except (InvalidOperation, ValueError, TypeError):
                    pass
        
        year_rate, created = HistoricalYearRate.objects.get_or_create(
            location=location,
            year=year,
            defaults={'updated_by': request.user}
        )
        
        # Log old values and update
        for field in price_fields:
            if field in request.data:
                new_value = request.data[field]
                old_value = getattr(year_rate, field) if not created else None
                
                if new_value is not None:
                    try:
                        new_value = Decimal(str(new_value))
                    except (InvalidOperation, ValueError, TypeError):
                        continue
                
                if old_value != new_value:
                    PriceHistoryLog.objects.create(
                        location=location,
                        location_name=location.location_name,
                        action='price_updated',
                        year=year,
                        field_name=field,
                        old_value=old_value,
                        new_value=new_value,
                        details=f'Updated {field} for {year} from {old_value} to {new_value}',
                        changed_by=request.user
                    )
                
                setattr(year_rate, field, new_value)
        
        year_rate.updated_by = request.user
        year_rate.save()
        
        return Response({
            'success': True,
            'message': f'Year {year} data updated successfully',
            'data': HistoricalYearRateSerializer(year_rate).data
        })
    
    def delete(self, request, location_id, year):
        """Delete a specific year"""
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
            year_rate = HistoricalYearRate.objects.get(location=location, year=year)
            
            # Log before deleting
            PriceHistoryLog.objects.create(
                location=location,
                location_name=location.location_name,
                action='year_deleted',
                year=year,
                details=f'Removed {year} data from {location.location_name}',
                changed_by=request.user
            )
            
            year_rate.delete()
            
            return Response({
                'success': True,
                'message': f'Year {year} deleted successfully'
            })
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except HistoricalYearRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Year data not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _get_year_comparison(self, location_id, year):
        """Compare with previous year"""
        try:
            current_year = HistoricalYearRate.objects.get(location_id=location_id, year=year)
            prev_year = HistoricalYearRate.objects.filter(
                location_id=location_id, 
                year=year-1
            ).first()
            
            if not prev_year:
                return None
            
            comparison = {}
            for field_name, label in [
                ('price_5_marla', '5 Marla'),
                ('price_10_marla', '10 Marla'),
                ('price_1_kanal', '1 Kanal'),
                ('price_2_kanal', '2 Kanal')
            ]:
                curr_val = getattr(current_year, field_name)
                prev_val = getattr(prev_year, field_name)
                
                if curr_val and prev_val and prev_val > 0:
                    change = curr_val - prev_val
                    change_percent = (change / prev_val) * 100
                    comparison[label] = {
                        'current': str(curr_val),
                        'previous': str(prev_val),
                        'change': str(change),
                        'change_percent': round(float(change_percent), 2)
                    }
            
            return comparison
        except HistoricalYearRate.DoesNotExist:
            return None


class BulkYearRatesView(APIView):
    """Bulk update multiple years at once (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request, location_id):
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        years_data = request.data.get('years', [])
        
        if not years_data:
            return Response({
                'success': False,
                'message': 'No years data provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = 0
        created_count = 0
        errors = []
        
        with transaction.atomic():
            for year_data in years_data:
                year = year_data.get('year')
                if not year:
                    continue
                
                try:
                    year = int(year)
                    if year < 2000 or year > 2100:
                        errors.append(f'Year {year} must be between 2000-2100')
                        continue
                except ValueError:
                    errors.append(f'Invalid year: {year}')
                    continue
                
                prices = {}
                for field in ['price_5_marla', 'price_10_marla', 'price_1_kanal', 'price_2_kanal']:
                    value = year_data.get(field)
                    if value is not None and value != '':
                        try:
                            decimal_value = Decimal(str(value))
                            if decimal_value > MAX_PRICE:
                                errors.append(f'{field} for year {year} exceeds 10 Crore limit')
                                continue
                            prices[field] = decimal_value
                        except (InvalidOperation, ValueError, TypeError):
                            errors.append(f'Invalid price for {field} in year {year}')
                            continue
                
                if errors:
                    continue
                
                year_rate, created = HistoricalYearRate.objects.update_or_create(
                    location=location,
                    year=year,
                    defaults={
                        **prices,
                        'updated_by': request.user
                    }
                )
                
                if created:
                    created_count += 1
                    PriceHistoryLog.objects.create(
                        location=location,
                        location_name=location.location_name,
                        action='year_added',
                        year=year,
                        details=f'Added {year} via bulk update',
                        changed_by=request.user
                    )
                else:
                    updated_count += 1
                    PriceHistoryLog.objects.create(
                        location=location,
                        location_name=location.location_name,
                        action='bulk_update',
                        year=year,
                        details=f'Updated {year} via bulk update',
                        changed_by=request.user
                    )
        
        response_data = {
            'success': True,
            'message': f'{created_count} years created, {updated_count} years updated',
            'created_count': created_count,
            'updated_count': updated_count,
            'total_processed': created_count + updated_count,
            'data': LocationRateSerializer(location).data
        }
        
        if errors:
            response_data['errors'] = errors
            response_data['success'] = len(errors) < len(years_data)
        
        return Response(response_data)


class DashboardStatsView(APIView):
    """Get dashboard statistics (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        total_locations = LocationRate.objects.count()
        total_records = HistoricalYearRate.objects.count()
        locations_with_data = LocationRate.objects.filter(years__isnull=False).distinct().count()
        
        all_years = list(HistoricalYearRate.objects.values_list('year', flat=True).distinct().order_by('year'))
        areas = list(LocationRate.objects.values_list('area_name', flat=True).distinct())
        cities = list(LocationRate.objects.values_list('city', flat=True).distinct())
        
        latest_updates = PriceHistoryLog.objects.all().order_by('-changed_at')[:20]
        
        price_stats = HistoricalYearRate.objects.aggregate(
            avg_price_5_marla=Avg('price_5_marla'),
            avg_price_10_marla=Avg('price_10_marla'),
            avg_price_1_kanal=Avg('price_1_kanal'),
            avg_price_2_kanal=Avg('price_2_kanal'),
            max_price_5_marla=Max('price_5_marla'),
            max_price_10_marla=Max('price_10_marla'),
            max_price_1_kanal=Max('price_1_kanal'),
            max_price_2_kanal=Max('price_2_kanal'),
        )
        
        # Convert to string for JSON
        for key, value in price_stats.items():
            if value is not None:
                price_stats[key] = str(value)
        
        today = datetime.now()
        this_month_activities = PriceHistoryLog.objects.filter(
            changed_at__month=today.month,
            changed_at__year=today.year
        ).count()
        
        return Response({
            'success': True,
            'data': {
                'total_locations': total_locations,
                'total_records': total_records,
                'locations_with_data': locations_with_data,
                'year_range': {
                    'min': min(all_years) if all_years else None,
                    'max': max(all_years) if all_years else None,
                    'all_years': all_years
                },
                'areas': areas,
                'cities': cities,
                'area_count': len(areas),
                'city_count': len(cities),
                'price_statistics': price_stats,
                'this_month_activities': this_month_activities,
                'recent_updates': PriceHistoryLogSerializer(latest_updates, many=True).data
            }
        })


class PriceHistoryLogView(APIView):
    """Get price change history (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, location_id=None):
        if location_id:
            try:
                location = LocationRate.objects.get(location_rate_id=location_id)
                logs = PriceHistoryLog.objects.filter(location=location).order_by('-changed_at')
            except LocationRate.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Location not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            logs = PriceHistoryLog.objects.all().order_by('-changed_at')
        
        # Search
        search = request.query_params.get('search', '')
        if search:
            logs = logs.filter(
                Q(location_name__icontains=search) |
                Q(details__icontains=search) |
                Q(action__icontains=search)
            )
        
        # Filter by action type
        action = request.query_params.get('action', '')
        if action:
            logs = logs.filter(action=action)
        
        # Filter by date range
        date_from = request.query_params.get('date_from', '')
        if date_from:
            logs = logs.filter(changed_at__date__gte=date_from)
        
        date_to = request.query_params.get('date_to', '')
        if date_to:
            logs = logs.filter(changed_at__date__lte=date_to)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        total_count = logs.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        logs_page = logs[start:end]
        serializer = PriceHistoryLogSerializer(logs_page, many=True)
        
        return Response({
            'success': True,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'data': serializer.data
        })


class LocationYearRangeView(APIView):
    """Get available years for a location (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, location_id):
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
            years = list(location.years.values_list('year', flat=True).order_by('-year'))
            
            year_stats = {}
            for y in years:
                year_data = location.years.filter(year=y).first()
                if year_data:
                    year_stats[str(y)] = {
                        'has_5_marla': bool(year_data.price_5_marla),
                        'has_10_marla': bool(year_data.price_10_marla),
                        'has_1_kanal': bool(year_data.price_1_kanal),
                        'has_2_kanal': bool(year_data.price_2_kanal),
                    }
            
            return Response({
                'success': True,
                'data': {
                    'location_id': location.location_rate_id,
                    'location_name': location.location_name,
                    'area_name': location.area_name,
                    'years': years,
                    'year_count': len(years),
                    'year_range': {
                        'min': min(years) if years else None,
                        'max': max(years) if years else None
                    },
                    'year_statistics': year_stats
                }
            })
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)


class YearComparisonView(APIView):
    """Compare prices between two years (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, location_id):
        try:
            location = LocationRate.objects.get(location_rate_id=location_id)
        except LocationRate.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Location not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        year1 = request.query_params.get('year1')
        year2 = request.query_params.get('year2')
        
        if not year1 or not year2:
            return Response({
                'success': False,
                'message': 'Both year1 and year2 are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year1 = int(year1)
            year2 = int(year2)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid year format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data_year1 = HistoricalYearRate.objects.get(location=location, year=year1)
            data_year2 = HistoricalYearRate.objects.get(location=location, year=year2)
        except HistoricalYearRate.DoesNotExist as e:
            return Response({
                'success': False,
                'message': f'Year data not found: {str(e)}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        comparison = {
            'location_name': location.location_name,
            'year1': year1,
            'year2': year2,
            'plots': {}
        }
        
        for plot_type, field_name in [
            ('5_marla', 'price_5_marla'),
            ('10_marla', 'price_10_marla'),
            ('1_kanal', 'price_1_kanal'),
            ('2_kanal', 'price_2_kanal')
        ]:
            price1 = getattr(data_year1, field_name)
            price2 = getattr(data_year2, field_name)
            
            if price1 and price2:
                change = price2 - price1
                change_percent = (change / price1 * 100) if price1 > 0 else 0
                
                comparison['plots'][plot_type] = {
                    f'price_{year1}': str(price1),
                    f'price_{year2}': str(price2),
                    'absolute_change': str(change),
                    'percentage_change': round(float(change_percent), 2),
                    'trend': 'up' if change > 0 else 'down' if change < 0 else 'stable'
                }
        
        return Response({
            'success': True,
            'data': comparison
        })


class ExportDataView(APIView):
    """Export data to CSV/JSON (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        export_type = request.query_params.get('type', 'all')
        format_type = request.query_params.get('format', 'csv')
        
        if export_type == 'location':
            location_id = request.query_params.get('location_id')
            if not location_id:
                return Response({
                    'success': False,
                    'message': 'location_id required for location export'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                location = LocationRate.objects.get(location_rate_id=location_id)
                data = self._export_location_data(location)
            except LocationRate.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Location not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            data = self._export_all_data()
        
        if format_type == 'csv':
            return self._generate_csv_response(data, export_type)
        else:
            return Response({
                'success': True,
                'data': data
            })
    
    def _export_location_data(self, location):
        years_data = []
        for year_rate in location.years.all().order_by('year'):
            years_data.append({
                'year': year_rate.year,
                'price_5_marla': str(year_rate.price_5_marla) if year_rate.price_5_marla else '',
                'price_10_marla': str(year_rate.price_10_marla) if year_rate.price_10_marla else '',
                'price_1_kanal': str(year_rate.price_1_kanal) if year_rate.price_1_kanal else '',
                'price_2_kanal': str(year_rate.price_2_kanal) if year_rate.price_2_kanal else '',
                'per_marla_5': str(year_rate.per_marla_rate_5) if year_rate.per_marla_rate_5 else '',
                'per_marla_10': str(year_rate.per_marla_rate_10) if year_rate.per_marla_rate_10 else '',
                'per_marla_1k': str(year_rate.per_marla_rate_1k) if year_rate.per_marla_rate_1k else '',
                'per_marla_2k': str(year_rate.per_marla_rate_2k) if year_rate.per_marla_rate_2k else '',
                'growth_5': str(year_rate.growth_percentage_5) if year_rate.growth_percentage_5 else '',
                'growth_10': str(year_rate.growth_percentage_10) if year_rate.growth_percentage_10 else '',
                'growth_1k': str(year_rate.growth_percentage_1k) if year_rate.growth_percentage_1k else '',
                'growth_2k': str(year_rate.growth_percentage_2k) if year_rate.growth_percentage_2k else '',
            })
        
        return {
            'location_name': location.location_name,
            'area_name': location.area_name,
            'city': location.city,
            'total_years': len(years_data),
            'years': years_data
        }
    
    def _export_all_data(self):
        locations_data = []
        for location in LocationRate.objects.prefetch_related('years').all():
            loc_data = self._export_location_data(location)
            locations_data.append(loc_data)
        
        return {
            'total_locations': len(locations_data),
            'locations': locations_data,
            'export_date': datetime.now().isoformat()
        }
    
    def _generate_csv_response(self, data, export_type):
        response = HttpResponse(content_type='text/csv')
        filename = f'historical_rates_{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        headers = [
            'Location Name', 'Area', 'City', 'Year',
            '5 Marla Price', '10 Marla Price', '1 Kanal Price', '2 Kanal Price',
            'Per Marla (5)', 'Per Marla (10)', 'Per Marla (1K)', 'Per Marla (2K)',
            'Growth % (5)', 'Growth % (10)', 'Growth % (1K)', 'Growth % (2K)'
        ]
        writer.writerow(headers)
        
        if export_type == 'location':
            locations = [data]
        else:
            locations = data.get('locations', [])
        
        for location in locations:
            for year_data in location.get('years', []):
                writer.writerow([
                    location['location_name'],
                    location['area_name'],
                    location.get('city', ''),
                    year_data['year'],
                    year_data['price_5_marla'],
                    year_data['price_10_marla'],
                    year_data['price_1_kanal'],
                    year_data['price_2_kanal'],
                    year_data.get('per_marla_5', ''),
                    year_data.get('per_marla_10', ''),
                    year_data.get('per_marla_1k', ''),
                    year_data.get('per_marla_2k', ''),
                    year_data.get('growth_5', ''),
                    year_data.get('growth_10', ''),
                    year_data.get('growth_1k', ''),
                    year_data.get('growth_2k', ''),
                ])
        
        return response


class ImportDataView(APIView):
    """Import data from CSV (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({
                'success': False,
                'message': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded_file))
            
            imported_locations = 0
            imported_years = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(csv_reader, start=2):
                    try:
                        location_name = row.get('Location Name', '').strip()
                        area_name = row.get('Area', '').strip()
                        city = row.get('City', 'Lahore').strip()
                        year = int(row.get('Year', 0))
                        
                        if not location_name or not area_name or not year:
                            errors.append(f'Row {row_num}: Missing required fields')
                            continue
                        
                        if year < 2000 or year > 2100:
                            errors.append(f'Row {row_num}: Invalid year {year}')
                            continue
                        
                        location, created = LocationRate.objects.get_or_create(
                            location_name__iexact=location_name,
                            defaults={
                                'location_name': location_name,
                                'area_name': area_name,
                                'city': city
                            }
                        )
                        
                        if created:
                            imported_locations += 1
                        
                        def parse_price(value):
                            if not value or value.strip() == '':
                                return None
                            try:
                                price = Decimal(str(value).replace(',', ''))
                                if price > MAX_PRICE:
                                    raise ValueError(f'Price exceeds 10 Crore limit')
                                return price
                            except (InvalidOperation, ValueError) as e:
                                raise ValueError(f'Invalid price: {value}')
                        
                        prices = {}
                        price_mapping = {
                            '5 Marla Price': 'price_5_marla',
                            '10 Marla Price': 'price_10_marla',
                            '1 Kanal Price': 'price_1_kanal',
                            '2 Kanal Price': 'price_2_kanal',
                        }
                        
                        for csv_field, model_field in price_mapping.items():
                            try:
                                prices[model_field] = parse_price(row.get(csv_field))
                            except ValueError as e:
                                errors.append(f'Row {row_num}: {str(e)}')
                                continue
                        
                        if errors:
                            continue
                        
                        year_rate, year_created = HistoricalYearRate.objects.update_or_create(
                            location=location,
                            year=year,
                            defaults={
                                **prices,
                                'updated_by': request.user
                            }
                        )
                        
                        if year_created:
                            imported_years += 1
                        
                        PriceHistoryLog.objects.create(
                            location=location,
                            location_name=location.location_name,
                            action='data_import',
                            year=year,
                            details=f'Imported {year} data from CSV',
                            changed_by=request.user
                        )
                        
                    except Exception as e:
                        errors.append(f'Row {row_num}: Unexpected error - {str(e)}')
            
            response_data = {
                'success': True,
                'message': f'Import completed: {imported_locations} locations, {imported_years} years',
                'imported_locations': imported_locations,
                'imported_years': imported_years,
                'total_rows_processed': row_num - 1 if 'row_num' in locals() else 0
            }
            
            if errors:
                response_data['errors'] = errors[:50]
                response_data['error_count'] = len(errors)
            
            return Response(response_data)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error processing file: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class AreaStatisticsView(APIView):
    """Get statistics grouped by area (Admin)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        areas = LocationRate.objects.values('area_name').annotate(
            location_count=models.Count('location_rate_id'),
            total_year_records=models.Count('years')
        ).order_by('area_name')
        
        area_details = []
        for area in areas:
            area_locations = LocationRate.objects.filter(area_name=area['area_name'])
            
            area_years = HistoricalYearRate.objects.filter(
                location__area_name=area['area_name']
            ).aggregate(
                min_year=Min('year'),
                max_year=Max('year')
            )
            
            latest_prices = {
                'avg_5_marla': 0,
                'avg_10_marla': 0,
                'avg_1_kanal': 0,
                'avg_2_kanal': 0,
                'count': 0
            }
            
            for loc in area_locations:
                latest = loc.years.order_by('-year').first()
                if latest:
                    latest_prices['count'] += 1
                    if latest.price_5_marla:
                        latest_prices['avg_5_marla'] += latest.price_5_marla
                    if latest.price_10_marla:
                        latest_prices['avg_10_marla'] += latest.price_10_marla
                    if latest.price_1_kanal:
                        latest_prices['avg_1_kanal'] += latest.price_1_kanal
                    if latest.price_2_kanal:
                        latest_prices['avg_2_kanal'] += latest.price_2_kanal
            
            if latest_prices['count'] > 0:
                for key in ['avg_5_marla', 'avg_10_marla', 'avg_1_kanal', 'avg_2_kanal']:
                    latest_prices[key] = str(round(float(latest_prices[key]) / latest_prices['count'], 2))
            
            area_details.append({
                'area_name': area['area_name'],
                'location_count': area['location_count'],
                'year_records': area['total_year_records'],
                'year_range': area_years,
                'average_latest_prices': latest_prices
            })  
        
        return Response({
            'success': True,
            'data': area_details
        })