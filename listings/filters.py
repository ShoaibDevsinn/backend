from django.db.models import Q
from .models import Listing

class ListingFilter:
    """
    Advanced filtering for listings
    """
    
    def __init__(self, queryset, request):
        self.queryset = queryset
        self.request = request
        self.params = request.query_params
    
    def filter(self):
        queryset = self.queryset
        
        # 1. Search by title, area, or description
        search = self.params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(location__location_name__icontains=search)
            )
        
        # 2. Location filter
        location = self.params.get('location')
        if location and location != 'all':
            queryset = queryset.filter(location_id=location)
        
        # 3. Price Range
        min_price = self.params.get('min_price')
        max_price = self.params.get('max_price')
        
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass
        
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass
        
        # 4. Bedrooms
        bedrooms = self.params.get('bedrooms')
        if bedrooms and bedrooms != 'any':
            try:
                queryset = queryset.filter(bedrooms__gte=int(bedrooms))
            except (ValueError, TypeError):
                pass
        
        # 5. Bathrooms
        bathrooms = self.params.get('bathrooms')
        if bathrooms and bathrooms != 'any':
            try:
                queryset = queryset.filter(bathrooms__gte=int(bathrooms))
            except (ValueError, TypeError):
                pass
        
        # 6. Kitchens
        kitchens = self.params.get('kitchens')
        if kitchens and kitchens != 'any':
            try:
                queryset = queryset.filter(kitchens__gte=int(kitchens))
            except (ValueError, TypeError):
                pass
        
        # 7. Marla Size Range
        min_marla = self.params.get('min_marla')
        max_marla = self.params.get('max_marla')
        
        if min_marla:
            try:
                queryset = queryset.filter(area_marla__gte=float(min_marla))
            except (ValueError, TypeError):
                pass
        
        if max_marla:
            try:
                queryset = queryset.filter(area_marla__lte=float(max_marla))
            except (ValueError, TypeError):
                pass
        
        # 8. Features / Amenities (Boolean filters)
        feature_mapping = {
            'has_lawn': 'has_lawn',
            'has_parking': 'has_parking',
            'has_security': 'has_security',
            'has_servant_quarter': 'has_servant_quarter',
            'has_study_room': 'has_study_room',
            'has_gym': 'has_gym',
            'has_swimming_pool': 'has_swimming_pool',
            'is_furnished': 'is_furnished',
            'has_dining_room': 'has_dining_room',
            'has_living_room': 'has_living_room',
            'has_electricity_backup': 'has_electricity_backup',
            'is_corner_plot': 'is_corner_plot',
            'is_facing_park': 'is_facing_park',
        }
        
        for param, field in feature_mapping.items():
            value = self.params.get(param)
            if value and value.lower() == 'true':
                queryset = queryset.filter(**{field: True})
        
        # 9. Property Status
        property_status = self.params.get('property_status')
        if property_status and property_status != 'all':
            queryset = queryset.filter(property_status=property_status)
        
        return queryset