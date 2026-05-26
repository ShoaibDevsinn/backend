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
    amenities = serializers.SerializerMethodField()
    custom_features_list = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Listing
        fields = [
            'listing_id', 'title', 'location', 'location_name',
            'area_marla', 'price', 'property_status', 'rent_price',
            'bedrooms', 'bathrooms', 'kitchens', 'construction_year',
            'number_of_floors', 'servant_rooms', 'store_rooms',
            'current_per_marla_rate', 'description',
            'has_lawn', 'has_parking', 'has_security', 'has_servant_quarter',
            'has_study_room', 'has_gym', 'has_swimming_pool', 'is_furnished',
            'has_dining_room', 'has_living_room', 'has_electricity_backup',
            'is_corner_plot', 'is_facing_park', 'custom_features',
            'amenities', 'custom_features_list', 'images', 'primary_image',
            'created_by', 'created_by_name',
            'created_at', 'updated_at', 'uploaded_images'
        ]
        read_only_fields = ['listing_id', 'created_at', 'updated_at']
        # ✅ REMOVE 'created_by' from read_only_fields so it can be set
    
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
        if data.get('property_status') == 'rent':
            if not data.get('rent_price'):
                raise serializers.ValidationError({
                    'rent_price': 'Rent price is required when property status is "Rent"'
                })
        return data
    
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        # ✅ created_by should already be in validated_data from serializer.save(created_by=...)
        listing = Listing.objects.create(**validated_data)
        
        for image in uploaded_images:
            ListingImage.objects.create(listing=listing, image_url=image)
        
        return listing
    
    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        for image in uploaded_images:
            ListingImage.objects.create(listing=instance, image_url=image)
        
        return instance


class ListingListSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.location_name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Listing
        fields = [
            'listing_id', 'title', 'location_name', 'area_marla',
            'price', 'property_status', 'rent_price', 'bedrooms',
            'bathrooms', 'kitchens', 'primary_image', 
            'created_by', 'created_by_name', 'created_at'
        ]
    
    def get_primary_image(self, obj):
        first_image = obj.images.first()
        if first_image and first_image.image_url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image_url.url)
            return first_image.image_url.url
        return None