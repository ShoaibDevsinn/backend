from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Prediction(models.Model):
    """Store user prediction requests"""
    prediction_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    
    # Input Features
    location = models.CharField(max_length=100)
    area_marla = models.DecimalField(max_digits=8, decimal_places=2)
    bedrooms = models.IntegerField(default=1)
    bathrooms = models.IntegerField(default=1)
    kitchens = models.IntegerField(default=1)
    construction_year = models.IntegerField(null=True, blank=True, default=2020)  # ← Added default
    number_of_floors = models.IntegerField(default=1)
    servant_rooms = models.IntegerField(default=0)
    store_rooms = models.IntegerField(default=0)
    
    # Amenities (Boolean)
    is_furnished = models.BooleanField(default=False)
    has_study_room = models.BooleanField(default=False)
    has_dining_room = models.BooleanField(default=False)
    has_swimming_pool = models.BooleanField(default=False)
    has_lounge = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)
    has_drawing_room = models.BooleanField(default=False)
    has_lawn = models.BooleanField(default=False)
    has_electricity_backup = models.BooleanField(default=False)
    
    # Special Features
    is_corner_plot = models.BooleanField(default=False)
    is_facing_park = models.BooleanField(default=False)
    
    # Prediction Results
    predicted_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    low_estimate = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    high_estimate = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    market_trend = models.CharField(max_length=50, null=True, blank=True)
    per_marla_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    key_factors = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'prediction'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Prediction #{self.prediction_id} - {self.location}"