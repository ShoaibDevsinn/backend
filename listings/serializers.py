from rest_framework import serializers
from .models import Listing, ListingImage, Location

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['location_id', 'location_name', 'city']


class ListingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ListingImage
        fields = ['image_id', 'image_url', 'uploaded_at']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image_url and request:
            return request.build_absolute_uri(obj.image_url.url)
        return obj.image_url.url if obj.image_url else None


class ListingSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True,
        default=list
    )
    location_name = serializers.CharField(source='location.location_name', read_only=True)
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    property_status_display = serializers.CharField(source='get_property_status_display', read_only=True)
    amenities = serializers.SerializerMethodField()
    custom_features_list = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Listing
        fields = [
            'listing_id', 'title', 'location', 'location_name',
            'area_marla', 'price', 'property_type', 'property_type_display',
            'property_status', 'property_status_display', 'rent_price',
            'bedrooms', 'bathrooms', 'kitchens', 'construction_year',
            'number_of_floors', 'servant_rooms', 'store_rooms',
            'current_per_marla_rate', 'description',
            'has_lawn', 'has_parking', 'has_security', 'has_servant_quarter',
            'has_study_room', 'has_gym', 'has_swimming_pool', 'is_furnished',
            'has_dining_room', 'has_living_room', 'has_electricity_backup',
            'is_corner_plot', 'is_facing_park', 'custom_features',
            'amenities', 'custom_features_list', 'images', 'primary_image',
            'created_by', 'created_by_name',
            'created_at', 'updated_at', 'uploaded_images',
            'expected_revenue', 'buyer_name'
        ]
        read_only_fields = ['listing_id', 'created_at', 'updated_at']
    
    def get_amenities(self, obj):
        amenities = []
        if obj.has_lawn: amenities.append('Lawn/Garden')
        if obj.has_parking: amenities.append('Parking')
        if obj.has_security: amenities.append('24/7 Security')
        if obj.has_servant_quarter: amenities.append('Servant Quarter')
        if obj.has_study_room: amenities.append('Study Room')
        if obj.has_gym: amenities.append('Gym')
        if obj.has_swimming_pool: amenities.append('Swimming Pool')
        if obj.is_furnished: amenities.append('Furnished')
        if obj.has_dining_room: amenities.append('Dining Room')
        if obj.has_living_room: amenities.append('Living Room')
        if obj.has_electricity_backup: amenities.append('Electricity Backup')
        if obj.is_corner_plot: amenities.append('Corner Plot')
        if obj.is_facing_park: amenities.append('Facing Park')
        return amenities
    
    def get_custom_features_list(self, obj):
        if obj.custom_features:
            return [feature.strip() for feature in obj.custom_features.split(',')]
        return []
    
    def get_primary_image(self, obj):
        first_image = obj.images.first()
        if first_image and first_image.image_url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image_url.url)
            return first_image.image_url.url
        return None
    
    def validate(self, data):
        # Get the instance for update operations
        instance = getattr(self, 'instance', None)
        
        # Get price value (from data or existing instance)
        price = data.get('price')
        if price is None and instance:
            price = instance.price
        
        expected_revenue = data.get('expected_revenue')
        if expected_revenue and price and expected_revenue > price:
            raise serializers.ValidationError({
                'expected_revenue': f'Expected revenue ({expected_revenue}) cannot be greater than property price ({price}). Please enter a reasonable profit margin.'
            })
        
        if expected_revenue and expected_revenue < 0:
            raise serializers.ValidationError({
                'expected_revenue': 'Expected revenue cannot be negative.'
            })
        
        # Validate rent price for rent properties
        if data.get('property_type') == 'rent':
            if not data.get('rent_price') or data.get('rent_price') <= 0:
                raise serializers.ValidationError({
                    'rent_price': 'Rent price is required when property type is "Rent"'
                })
        
        # Get property status (from data or existing instance)
        property_status = data.get('property_status')
        if property_status is None and instance:
            property_status = instance.property_status
        
        buyer_name = data.get('buyer_name')
        
        if property_status == 'sold':
            # Validate price exists
            if not price or price <= 0:
                raise serializers.ValidationError({
                    'price': 'Price is required when property status is "Sold"'
                })
            
            # Validate buyer name is provided
            if not buyer_name:
                raise serializers.ValidationError({
                    'buyer_name': 'Buyer name is required when property status is "Sold"'
                })
            
            # Validate buyer name is not empty string
            if buyer_name and not buyer_name.strip():
                raise serializers.ValidationError({
                    'buyer_name': 'Buyer name cannot be empty'
                })
        
        if property_status == 'sold' and not expected_revenue:
            # This is a warning, not an error - you can still save
            # But you might want to add a warning in the response
            pass
        
        return data
    
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        listing = Listing.objects.create(**validated_data)
        
        for image in uploaded_images:
            ListingImage.objects.create(listing=listing, image_url=image)
        
        return listing
    
    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        # Handle status change
        old_status = instance.property_status
        new_status = validated_data.get('property_status', old_status)
        
        if old_status != 'sold' and new_status == 'sold':
            revenue = validated_data.get('expected_revenue', instance.expected_revenue)
            buyer = validated_data.get('buyer_name', instance.buyer_name)
            print(f"   Property {instance.listing_id} marked as SOLD!")
            print(f"   Buyer: {buyer}")
            print(f"   Expected Revenue: {revenue}")
            print(f"   Property Price: {instance.price}")
        
        # Update all fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Add new images
        for image in uploaded_images:
            ListingImage.objects.create(listing=instance, image_url=image)
        
        return instance


class ListingListSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.location_name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    property_status_display = serializers.CharField(source='get_property_status_display', read_only=True)
    
    class Meta:
        model = Listing
        fields = [
            'listing_id', 'title', 'location_name', 'area_marla',
            'price', 'property_type', 'property_type_display',
            'property_status', 'property_status_display', 'rent_price', 
            'bedrooms', 'bathrooms', 'kitchens', 'primary_image', 
            'created_by', 'created_by_name', 'created_at', 'current_per_marla_rate',
            'expected_revenue', 'buyer_name'
        ]
    
    def get_primary_image(self, obj):
        first_image = obj.images.first()
        if first_image and first_image.image_url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image_url.url)
            return first_image.image_url.url
        return None