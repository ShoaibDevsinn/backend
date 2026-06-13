from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsAdminUser
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import models
from .models import Location, Listing, ListingImage
from .serializers import (
    LocationSerializer, ListingSerializer, 
    ListingListSerializer
)
from .filters import ListingFilter
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta


class LocationListView(APIView):
    permission_classes = [AllowAny] 
    
    def get(self, request):
        locations = Location.objects.all().order_by('location_name')
        serializer = LocationSerializer(locations, many=True)
        return Response({
            'success': True,
            'count': locations.count(),
            'data': serializer.data
        })


class AdminAddListingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
            data = request.data.copy()
            
            # Handle boolean fields
            boolean_fields = [
                'has_lawn', 'has_parking', 'has_security', 'has_servant_quarter',
                'has_study_room', 'has_gym', 'has_swimming_pool', 'is_furnished',
                'has_dining_room', 'has_living_room', 'has_electricity_backup',
                'is_corner_plot', 'is_facing_park'
            ]
            
            for field in boolean_fields:
                if field in data:
                    val = data[field]
                    if isinstance(val, str):
                        data[field] = val.lower() in ['true', '1', 'on', 'yes']
            
            # Handle number fields
            number_fields = ['bedrooms', 'bathrooms', 'kitchens', 'number_of_floors', 
                           'servant_rooms', 'store_rooms']
            for field in number_fields:
                if field in data and data[field]:
                    try:
                        data[field] = int(data[field])
                    except (ValueError, TypeError):
                        data[field] = 0
            
            # Handle decimal fields
            decimal_fields = ['area_marla', 'price', 'rent_price', 'current_per_marla_rate', 'expected_revenue']
            for field in decimal_fields:
                if field in data and data[field]:
                    try:
                        data[field] = float(data[field])
                    except (ValueError, TypeError):
                        data[field] = 0
            
            # Handle images
            uploaded_images = request.FILES.getlist('images')
            if uploaded_images:
                data.setlist('uploaded_images', uploaded_images)
            
            serializer = ListingSerializer(data=data, context={'request': request})
            
            if serializer.is_valid():
                listing = serializer.save(created_by=request.user)
                
                print(f"Listing created: ID={listing.listing_id}, Title={listing.title}, Created by={listing.created_by}")
                if listing.expected_revenue:
                    print(f"Expected Revenue: {listing.expected_revenue}")
                
                return Response({
                    'success': True,
                    'message': 'Property listing created successfully',
                    'data': ListingSerializer(listing, context={'request': request}).data
                }, status=status.HTTP_201_CREATED)
            
            print(f"Serializer errors: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            import traceback
            print(f"Error creating listing: {str(e)}")
            print(traceback.format_exc())
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminGetListingsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        listings = Listing.objects.filter(
            created_by=request.user
        ).select_related('location').prefetch_related('images').order_by('-created_at')
        
        # Add property_type filter
        property_type = request.query_params.get('property_type')
        if property_type:
            listings = listings.filter(property_type=property_type)
        
        # Add property_status filter
        property_status = request.query_params.get('property_status')
        if property_status:
            listings = listings.filter(property_status=property_status)
        
        serializer = ListingListSerializer(listings, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': listings.count(),
            'data': serializer.data
        })


class AdminGetListingDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, listing_id):
        try:
            listing = Listing.objects.select_related('location').prefetch_related('images').get(
                listing_id=listing_id,
                created_by=request.user
            )
            serializer = ListingSerializer(listing, context={'request': request})
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Listing.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Listing not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminUpdateListingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    
    def put(self, request, listing_id):
        try:
            listing = Listing.objects.get(
                listing_id=listing_id,
                created_by=request.user
            )
        except Listing.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Listing not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data.copy()
        
        # Handle boolean fields
        boolean_fields = [
            'has_lawn', 'has_parking', 'has_security', 'has_servant_quarter',
            'has_study_room', 'has_gym', 'has_swimming_pool', 'is_furnished',
            'has_dining_room', 'has_living_room', 'has_electricity_backup',
            'is_corner_plot', 'is_facing_park'
        ]
        
        for field in boolean_fields:
            if field in data:
                val = data[field]
                if isinstance(val, str):
                    data[field] = val.lower() in ['true', '1', 'on', 'yes']
        
        # Handle number fields
        number_fields = ['bedrooms', 'bathrooms', 'kitchens', 'number_of_floors', 
                       'servant_rooms', 'store_rooms']
        for field in number_fields:
            if field in data and data[field]:
                try:
                    data[field] = int(data[field])
                except (ValueError, TypeError):
                    pass
        
        # Handle decimal fields including expected_revenue
        decimal_fields = ['area_marla', 'price', 'rent_price', 'current_per_marla_rate', 'expected_revenue']
        for field in decimal_fields:
            if field in data and data[field]:
                try:
                    data[field] = float(data[field])
                except (ValueError, TypeError):
                    pass
        
        # Handle images
        uploaded_images = request.FILES.getlist('images')
        if uploaded_images:
            data.setlist('uploaded_images', uploaded_images)
        
        serializer = ListingSerializer(listing, data=data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            updated_listing = serializer.save()
            
            # Log revenue information when property is marked as sold
            if data.get('property_status') == 'sold' and updated_listing.expected_revenue:
                print(f"💰 Revenue added from property {listing_id}: {updated_listing.expected_revenue}")
                print(f"   Buyer: {updated_listing.buyer_name}")
            
            return Response({
                'success': True,
                'message': 'Listing updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminDeleteListingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def delete(self, request, listing_id):
        try:
            listing = Listing.objects.get(
                listing_id=listing_id,
                created_by=request.user
            )
            listing.delete()
            return Response({
                'success': True,
                'message': 'Listing deleted successfully'
            })
        except Listing.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Listing not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminDeleteListingImageView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def delete(self, request, image_id):
        try:
            image = ListingImage.objects.select_related('listing').get(
                image_id=image_id,
                listing__created_by=request.user
            )
            image.delete()
            return Response({
                'success': True,
                'message': 'Image deleted successfully'
            })
        except ListingImage.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Image not found'
            }, status=status.HTTP_404_NOT_FOUND)


class PublicGetListingsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        listings = Listing.objects.select_related('location').prefetch_related('images').filter(
            ~Q(property_status='sold')
        ).order_by('-created_at')
        serializer = ListingListSerializer(listings, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': listings.count(),
            'data': serializer.data
        })


class PublicGetListingDetailView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, listing_id):
        try:
            listing = Listing.objects.select_related('location').prefetch_related('images').get(listing_id=listing_id)
            serializer = ListingSerializer(listing, context={'request': request})
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Listing.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Listing not found'
            }, status=status.HTTP_404_NOT_FOUND)


class PublicFilteredListingsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        queryset = Listing.objects.select_related('location').prefetch_related('images').filter(
            ~Q(property_status='sold')
        )
        
        filter_instance = ListingFilter(queryset, request)
        filtered_queryset = filter_instance.filter()
        
        order_by = request.query_params.get('order_by', '-created_at')
        if order_by in ['price', '-price', 'created_at', '-created_at', 'area_marla', '-area_marla']:
            filtered_queryset = filtered_queryset.order_by(order_by)
        else:
            filtered_queryset = filtered_queryset.order_by('-created_at')
        
        serializer = ListingListSerializer(filtered_queryset, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'count': filtered_queryset.count(),
            'filters_applied': dict(request.query_params),
            'data': serializer.data
        })
    

class AdminFilteredListingsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        queryset = Listing.objects.filter(
            created_by=request.user
        ).select_related('location').prefetch_related('images')
        
        filter_instance = ListingFilter(queryset, request)
        filtered_queryset = filter_instance.filter()
        
        order_by = request.query_params.get('order_by', '-created_at')
        if order_by in ['price', '-price', 'created_at', '-created_at', 'area_marla', '-area_marla']:
            filtered_queryset = filtered_queryset.order_by(order_by)
        else:
            filtered_queryset = filtered_queryset.order_by('-created_at')
        
        serializer = ListingListSerializer(filtered_queryset, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'count': filtered_queryset.count(),
            'filters_applied': dict(request.query_params),
            'data': serializer.data
        })


class FilterOptionsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        listings = Listing.objects.all()
        
        price_range = listings.aggregate(
            min_price=models.Min('price'),
            max_price=models.Max('price')
        )
        
        marla_range = listings.aggregate(
            min_marla=models.Min('area_marla'),
            max_marla=models.Max('area_marla')
        )
        
        bedroom_options = listings.values_list('bedrooms', flat=True).distinct().order_by('bedrooms')
        bathroom_options = listings.values_list('bathrooms', flat=True).distinct().order_by('bathrooms')
        
        return Response({
            'success': True,
            'data': {
                'price_range': {
                    'min': float(price_range['min_price']) if price_range['min_price'] else 0,
                    'max': float(price_range['max_price']) if price_range['max_price'] else 0
                },
                'marla_range': {
                    'min': float(marla_range['min_marla']) if marla_range['min_marla'] else 0,
                    'max': float(marla_range['max_marla']) if marla_range['max_marla'] else 0
                },
                'bedroom_options': list(bedroom_options),
                'bathroom_options': list(bathroom_options),
                'feature_options': [
                    {'key': 'has_lawn', 'label': 'Lawn/Garden'},
                    {'key': 'has_parking', 'label': 'Parking'},
                    {'key': 'has_security', 'label': '24/7 Security'},
                    {'key': 'has_servant_quarter', 'label': 'Servant Quarter'},
                    {'key': 'has_study_room', 'label': 'Study Room'},
                    {'key': 'has_gym', 'label': 'Gym'},
                    {'key': 'has_swimming_pool', 'label': 'Swimming Pool'},
                    {'key': 'is_furnished', 'label': 'Furnished'},
                    {'key': 'has_dining_room', 'label': 'Dining Room'},
                    {'key': 'has_living_room', 'label': 'Living Room'},
                    {'key': 'has_electricity_backup', 'label': 'Electricity Backup'},
                    {'key': 'is_corner_plot', 'label': 'Corner Plot'},
                    {'key': 'is_facing_park', 'label': 'Facing Park'},
                ]
            }
        })


class AdminDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        listings = Listing.objects.filter(created_by=request.user)
        
        total_properties = listings.count()
        sold_properties = listings.filter(property_status='sold').count()
        active_listings = listings.filter(property_status='available').count()
        rent_listings = listings.filter(property_type='rent').count()
        
        total_revenue = listings.filter(
            property_status='sold',
            expected_revenue__isnull=False
        ).aggregate(
            total=models.Sum('expected_revenue')
        )['total'] or 0
        
        total_profit = listings.filter(
            property_status='sold',
            expected_revenue__isnull=False
        ).aggregate(
            total=models.Sum('expected_revenue')
        )['total'] or 0
        
        recent_listings = listings.order_by('-created_at')[:5]
        recent_serializer = ListingListSerializer(recent_listings, many=True, context={'request': request})
        
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_stats = listings.filter(created_at__gte=six_months_ago).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('listing_id'),
            revenue=Sum('expected_revenue', filter=Q(property_status='sold'))
        ).order_by('month')
        
        return Response({
            'success': True,
            'data': {
                'total_properties': total_properties,
                'sold_properties': sold_properties,
                'active_listings': active_listings,
                'rent_listings': rent_listings,
                'total_revenue': float(total_revenue),
                'total_profit': float(total_profit),
                'recent_listings': recent_serializer.data,
                'monthly_stats': list(monthly_stats)
            }
        })


class PublicStatisticsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get ALL properties for statistics (including sold)
        all_listings = Listing.objects.select_related('location').prefetch_related('images').all()
        
        total_properties = all_listings.count()
        sold_properties = all_listings.filter(property_status='sold').count()
        available_properties = all_listings.filter(property_status='available').count()
        
        # Calculate price statistics from ALL properties (including sold)
        prices = all_listings.filter(price__isnull=False).exclude(price=0).values_list('price', flat=True)
        
        # Calculate max price from available properties only (for display)
        available_prices = all_listings.filter(
            property_status='available',
            price__isnull=False
        ).exclude(price=0).values_list('price', flat=True)
        
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices) if prices else 0
            max_available_price = max(available_prices) if available_prices else max_price
        else:
            avg_price = min_price = max_price = max_available_price = 0
        
        total_revenue = all_listings.filter(
            property_status='sold',
            expected_revenue__isnull=False
        ).aggregate(
            total=models.Sum('expected_revenue')
        )['total'] or 0
        
        return Response({
            'success': True,
            'data': {
                'total_properties': total_properties,
                'sold_properties': sold_properties,
                'available_properties': available_properties,
                'avg_price': float(avg_price),
                'min_price': float(min_price),
                'max_price': float(max_available_price),  # Max price of available properties
                'total_revenue': float(total_revenue),
            }
        })