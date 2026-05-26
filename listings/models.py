from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class Location(models.Model):
    location_id = models.AutoField(primary_key=True)
    location_name = models.CharField(max_length=100)
    city = models.CharField(max_length=50, default='Lahore')
    
    class Meta:
        db_table = 'location'
        managed = False
        
    def __str__(self):
        return self.location_name


class ListingImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, related_name='images', db_column='listing_id')
    image_url = models.ImageField(upload_to='property_images/', max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'listing_image'
        
    def __str__(self):
        return f"Image for {self.listing.title}"


class Listing(models.Model):
    # Status Choices
    PROPERTY_STATUS_CHOICES = [
        ('available', 'Available'),
        ('rent', 'For Rent'),
        ('sold', 'Sold'),
    ]
    
    # Basic Information
    listing_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, db_column='location_id')
    area_marla = models.DecimalField(max_digits=8, decimal_places=2, help_text="Area in Marlas")
    price = models.DecimalField(max_digits=15, decimal_places=2, help_text="Sale Price")
    property_status = models.CharField(max_length=10, choices=PROPERTY_STATUS_CHOICES, default='available')
    rent_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Monthly rent (if applicable)")
    
    # Property Details
    bedrooms = models.IntegerField(default=1)
    bathrooms = models.IntegerField(default=1)
    kitchens = models.IntegerField(default=1)
    construction_year = models.IntegerField(null=True, blank=True)
    number_of_floors = models.IntegerField(default=1)
    servant_rooms = models.IntegerField(default=0)
    store_rooms = models.IntegerField(default=0)
    current_per_marla_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Amenities (Boolean fields)
    has_lawn = models.BooleanField(default=False)
    has_parking = models.BooleanField(default=False)
    has_security = models.BooleanField(default=False)
    has_servant_quarter = models.BooleanField(default=False)
    has_study_room = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)
    has_swimming_pool = models.BooleanField(default=False)
    is_furnished = models.BooleanField(default=False)
    has_dining_room = models.BooleanField(default=False)
    has_living_room = models.BooleanField(default=False)
    has_electricity_backup = models.BooleanField(default=False)
    
    # Special Features
    is_corner_plot = models.BooleanField(default=False)
    is_facing_park = models.BooleanField(default=False)
    custom_features = models.TextField(null=True, blank=True, help_text="Comma-separated custom features")
    
    # Description
    description = models.TextField()
    
    # ✅ FIXED: ForeignKey to User model instead of IntegerField
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='listings',
        db_column='created_by_id',
        null=True, 
        blank=True
    )
    
    # Keep old field for backward compatibility
    admin_id = models.IntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'listing'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    @property
    def image_urls(self):
        """Return list of image URLs for this listing"""
        return [img.image_url.url for img in self.images.all()]
    
    @property
    def amenities_list(self):
        """Return list of enabled amenities"""
        amenities = []
        if self.has_lawn: amenities.append('Lawn/Garden')
        if self.has_parking: amenities.append('Parking')
        if self.has_security: amenities.append('24/7 Security')
        if self.has_servant_quarter: amenities.append('Servant Quarter')
        if self.has_study_room: amenities.append('Study Room')
        if self.has_gym: amenities.append('Gym')
        if self.has_swimming_pool: amenities.append('Swimming Pool')
        if self.is_furnished: amenities.append('Furnished')
        if self.has_dining_room: amenities.append('Dining Room')
        if self.has_living_room: amenities.append('Living Room')
        if self.has_electricity_backup: amenities.append('Electricity Backup')
        return amenities