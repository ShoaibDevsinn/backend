# H:\Backend\predictions\serializers.py
from rest_framework import serializers
from .models import Prediction

class PredictionRequestSerializer(serializers.Serializer):
    """Validate input from frontend"""
    # Required fields
    location = serializers.CharField(max_length=100, required=True)
    area_marla = serializers.FloatField(required=True, min_value=0.01)  # Changed min_value to 0.01
    bedrooms = serializers.IntegerField(default=1, min_value=1)  # Changed min_value to 1
    bathrooms = serializers.IntegerField(default=1, min_value=1)  # Changed min_value to 1
    kitchens = serializers.IntegerField(default=1, min_value=1)  # Changed min_value to 1
    
    # Optional fields with defaults
    construction_year = serializers.IntegerField(required=False, allow_null=True, default=2020)
    number_of_floors = serializers.IntegerField(default=1, min_value=1)
    servant_rooms = serializers.IntegerField(default=0, min_value=0)
    store_rooms = serializers.IntegerField(default=0, min_value=0)
    
    # Amenities (Boolean)
    is_furnished = serializers.BooleanField(default=False, required=False)
    has_study_room = serializers.BooleanField(default=False, required=False)
    has_dining_room = serializers.BooleanField(default=False, required=False)
    has_swimming_pool = serializers.BooleanField(default=False, required=False)
    has_lounge = serializers.BooleanField(default=False, required=False)
    has_gym = serializers.BooleanField(default=False, required=False)
    has_drawing_room = serializers.BooleanField(default=False, required=False)
    has_lawn = serializers.BooleanField(default=False, required=False)
    has_electricity_backup = serializers.BooleanField(default=False, required=False)
    
    # Special Features
    is_corner_plot = serializers.BooleanField(default=False, required=False)
    is_facing_park = serializers.BooleanField(default=False, required=False)
    
    def validate_area_marla(self, value):
        """Validate area is positive"""
        if value <= 0:
            raise serializers.ValidationError("Area must be greater than 0")
        if value > 1000:
            raise serializers.ValidationError("Area seems too large (> 1000 Marla). Please verify.")
        return value
    
    def validate_construction_year(self, value):
        """Validate construction year is reasonable"""
        if value is None:
            return 2020
        current_year = 2025
        if value < 1900:
            raise serializers.ValidationError("Construction year cannot be before 1900")
        if value > current_year + 1:
            raise serializers.ValidationError(f"Construction year cannot be in the future (max {current_year})")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Ensure bathrooms don't exceed bedrooms by too much (unrealistic)
        bedrooms = data.get('bedrooms', 1)
        bathrooms = data.get('bathrooms', 1)
        
        if bathrooms > bedrooms * 2:
            raise serializers.ValidationError({
                'bathrooms': f"Bathrooms ({bathrooms}) cannot exceed bedrooms ({bedrooms}) by more than double"
            })
        
        # Validate number of floors is reasonable
        floors = data.get('number_of_floors', 1)
        if floors > 5:
            raise serializers.ValidationError({
                'number_of_floors': "Number of floors cannot exceed 5"
            })
        
        return data


class PredictionResponseSerializer(serializers.ModelSerializer):
    """For returning prediction results"""
    predicted_price_display = serializers.SerializerMethodField()
    low_estimate_display = serializers.SerializerMethodField()
    high_estimate_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Prediction
        fields = [
            'prediction_id',
            'location',
            'area_marla',
            'bedrooms',
            'bathrooms',
            'kitchens',
            'construction_year',
            'number_of_floors',
            'servant_rooms',
            'store_rooms',
            'is_furnished',
            'has_study_room',
            'has_dining_room',
            'has_swimming_pool',
            'has_lounge',
            'has_gym',
            'has_drawing_room',
            'has_lawn',
            'has_electricity_backup',
            'is_corner_plot',
            'is_facing_park',
            'predicted_price',
            'low_estimate',
            'high_estimate',
            'confidence_score',
            'market_trend',
            'per_marla_rate',
            'key_factors',
            'created_at',
            'predicted_price_display',
            'low_estimate_display',
            'high_estimate_display',
        ]
        read_only_fields = fields
    
    def get_predicted_price_display(self, obj):
        """Return formatted price in Crores/Lakhs"""
        if obj.predicted_price:
            price = float(obj.predicted_price)
            if price >= 10_000_000:
                crores = price / 10_000_000
                return f"{crores:.2f} Crore"
            else:
                lakhs = price / 100_000
                return f"{lakhs:.2f} Lakh"
        return None
    
    def get_low_estimate_display(self, obj):
        """Return formatted low estimate"""
        if obj.low_estimate:
            price = float(obj.low_estimate)
            if price >= 10_000_000:
                crores = price / 10_000_000
                return f"{crores:.2f} Crore"
            else:
                lakhs = price / 100_000
                return f"{lakhs:.2f} Lakh"
        return None
    
    def get_high_estimate_display(self, obj):
        """Return formatted high estimate"""
        if obj.high_estimate:
            price = float(obj.high_estimate)
            if price >= 10_000_000:
                crores = price / 10_000_000
                return f"{crores:.2f} Crore"
            else:
                lakhs = price / 100_000
                return f"{lakhs:.2f} Lakh"
        return None


class PredictionHistorySerializer(serializers.ModelSerializer):
    """For listing past predictions"""
    predicted_price_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Prediction
        fields = [
            'prediction_id',
            'location',
            'area_marla',
            'bedrooms',
            'bathrooms',
            'kitchens',
            'predicted_price',
            'predicted_price_display',
            'confidence_score',
            'market_trend',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_predicted_price_display(self, obj):
        """Return formatted price in Crores/Lakhs"""
        if obj.predicted_price:
            price = float(obj.predicted_price)
            if price >= 10_000_000:
                crores = price / 10_000_000
                return f"{crores:.2f} Crore"
            else:
                lakhs = price / 100_000
                return f"{lakhs:.2f} Lakh"
        return None


class SavePredictionSerializer(serializers.Serializer):
    """For saving a prediction"""
    prediction_result = serializers.DictField(required=True)
    input_data = serializers.DictField(required=True)
    
    def validate_prediction_result(self, value):
        """Validate prediction result contains required fields"""
        required_fields = ['estimated_market_value', 'confidence_percentage', 
                          'market_trend', 'low_estimate', 'high_estimate']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing field in prediction_result: {field}")
        return value
    
    def validate_input_data(self, value):
        """Validate input data contains required fields"""
        required_fields = ['location', 'area_marla', 'bedrooms', 'bathrooms', 'kitchens']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing field in input_data: {field}")
        return value