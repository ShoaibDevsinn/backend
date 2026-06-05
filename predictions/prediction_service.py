# H:\Backend\predictions\prediction_service.py
import joblib
import pandas as pd
import numpy as np
import os
from pathlib import Path

class PropertyPricePredictor:
    """
    Uses the retrained XGBoost model (compatible with scikit-learn 1.8.0)
    """
    
    def __init__(self):
        """Load the retrained model"""
        base_dir = Path(__file__).parent
        models_dir = base_dir / 'models'
        
        pipeline_path = models_dir / 'property_price_pipeline.pkl'
        
        if not pipeline_path.exists():
            raise FileNotFoundError(
                f"Model not found at {pipeline_path}\n"
                "Please run 'python predictions/retrain_model.py' first."
            )
        
        self.pipeline = joblib.load(pipeline_path)
        
        # Load feature columns
        feature_cols_path = models_dir / 'feature_columns.pkl'
        if feature_cols_path.exists():
            self.feature_columns = joblib.load(feature_cols_path)
        
        print(f"✅ Model loaded successfully from {pipeline_path}")
    
    def _convert_to_native(self, value):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(value, np.floating):
            return float(value)
        elif isinstance(value, np.integer):
            return int(value)
        elif isinstance(value, np.ndarray):
            return value.tolist()
        return value
    
    def predict(self, property_data):
        """
        Make price prediction using the trained model
        
        Args:
            property_data: dict with property features
            
        Returns:
            dict with prediction results (all values JSON serializable)
        """
        
        CURRENT_YEAR = 2025
        
        # Extract basic info
        area_marla = float(property_data.get('area_marla', 0))
        if area_marla <= 0:
            raise ValueError("Area must be greater than 0")
        
        area_sqft = area_marla * 272.25
        
        # Construction year handling
        construction_year = property_data.get('construction_year', CURRENT_YEAR)
        if construction_year is None:
            construction_year = CURRENT_YEAR
        house_age = max(0, CURRENT_YEAR - int(construction_year))
        
        # Amenities
        amenities = {
            'gym': property_data.get('has_gym', False),
            'study_room': property_data.get('has_study_room', False),
            'drawing_room': property_data.get('has_drawing_room', False),
            'dining_room': property_data.get('has_dining_room', False),
            'lawn_garden': property_data.get('has_lawn', False),
            'swimming_pool': property_data.get('has_swimming_pool', False),
            'electricity_backup': property_data.get('has_electricity_backup', False),
            'lounge_sitting': property_data.get('has_lounge', False),
        }
        
        total_amenities = sum(1 for v in amenities.values() if v)
        
        bedrooms = property_data.get('bedrooms', 1)
        bathrooms = property_data.get('bathrooms', 1)
        num_floors = property_data.get('number_of_floors', 1)
        kitchens = property_data.get('kitchens', 1)
        servant_rooms = property_data.get('servant_rooms', 0)
        store_rooms = property_data.get('store_rooms', 0)
        
        # Derived features (matching training)
        area_per_bedroom = area_sqft / max(bedrooms, 1)
        bathroom_ratio = bathrooms / max(bedrooms, 1)
        beds_x_floors = bedrooms * num_floors
        age_x_amenities = house_age * total_amenities
        
        # Build features DataFrame (must match training columns exactly)
        features = pd.DataFrame([{
            'Main_Location': property_data.get('location', 'Other'),
            'Area_SqFt': area_sqft,
            'Bedrooms': bedrooms,
            'Bathrooms': bathrooms,
            'Kitchens': kitchens,
            'House_Age': house_age,
            'Num_Floors': num_floors,
            'Servant Quarters': servant_rooms,
            'Store Rooms': store_rooms,
            'Furnished': 1 if property_data.get('is_furnished', False) else 0,
            'Gym': 1 if amenities['gym'] else 0,
            'Study Room': 1 if amenities['study_room'] else 0,
            'Drawing Room': 1 if amenities['drawing_room'] else 0,
            'Dining Room': 1 if amenities['dining_room'] else 0,
            'Lawn/Garden': 1 if amenities['lawn_garden'] else 0,
            'Swimming Pool': 1 if amenities['swimming_pool'] else 0,
            'Electricity Backup': 1 if amenities['electricity_backup'] else 0,
            'Lounge/Sitting Room': 1 if amenities['lounge_sitting'] else 0,
            'Total_Amenities': total_amenities,
            'Is_Corner': 1 if property_data.get('is_corner_plot', False) else 0,
            'Facing_Park': 1 if property_data.get('is_facing_park', False) else 0,
            'Area_per_Bedroom': area_per_bedroom,
            'Bathroom_Ratio': bathroom_ratio,
            'Beds_x_Floors': beds_x_floors,
            'Age_x_Amenities': age_x_amenities,
        }])
        
        # Ensure column order matches training
        if hasattr(self, 'feature_columns') and self.feature_columns:
            features = features[self.feature_columns]
        
        # Make prediction (model outputs log1p price)
        pred_log = self.pipeline.predict(features)[0]
        
        # Convert numpy float32 to Python float
        pred_log = float(pred_log)
        
        # Convert to actual price
        predicted_price = np.expm1(pred_log)
        predicted_price = float(predicted_price)  # Convert to Python float
        
        # Calculate bounds (±12% for real estate)
        margin_pct = 12
        lower_bound = predicted_price * (1 - margin_pct / 100)
        upper_bound = predicted_price * (1 + margin_pct / 100)
        
        # Ensure bounds are Python floats
        lower_bound = float(lower_bound)
        upper_bound = float(upper_bound)
        
        # Determine market trend
        if predicted_price < 5_000_000:
            market_trend = "Affordable"
        elif predicted_price < 15_000_000:
            market_trend = "Mid-Range"
        elif predicted_price < 40_000_000:
            market_trend = "Premium"
        else:
            market_trend = "Luxury"
        
        # Generate key factors
        key_factors = self._generate_key_factors(
            property_data, predicted_price, area_marla
        )
        
        # Confidence score (based on model R² = 0.83)
        confidence = 88.0
        
        # Calculate per marla rate
        per_marla_rate = predicted_price / area_marla if area_marla > 0 else 0
        per_marla_rate = float(per_marla_rate)
        
        return {
            'estimated_market_value': predicted_price,
            'confidence_percentage': confidence,
            'market_trend': market_trend,
            'low_estimate': lower_bound,
            'high_estimate': upper_bound,
            'key_factors': key_factors,
            'per_marla_rate': per_marla_rate,
        }
    
    def _generate_key_factors(self, data, price, area_marla):
        """Generate human-readable key factors"""
        factors = []
        
        # Price per marla
        if area_marla > 0:
            factors.append(f"PKR {price/area_marla:,.0f} per Marla")
        
        # Location quality
        location = data.get('location', '')
        if 'DHA' in location.upper() or 'DEFENCE' in location.upper():
            factors.append("Prime location: DHA/Defence")
        elif 'BAHRIA' in location.upper():
            factors.append("Premium location: Bahria Town")
        
        # Special features
        if data.get('is_corner_plot', False):
            factors.append("Corner plot (+5% value)")
        
        if data.get('is_facing_park', False):
            factors.append("Park-facing (+4% value)")
        
        if data.get('is_furnished', False):
            factors.append("Fully furnished (+8% value)")
        
        if data.get('has_swimming_pool', False):
            factors.append("Swimming pool (+6% value)")
        
        if data.get('has_gym', False):
            factors.append("Gym facility (+3% value)")
        
        # Multiple floors
        num_floors = data.get('number_of_floors', 1)
        if num_floors >= 2:
            factors.append(f"{num_floors} floors (+{num_floors * 3}% value)")
        
        if not factors:
            factors.append("Standard residential property")
        
        return "; ".join(factors[:5])


# Singleton instance
_predictor = None

def get_predictor():
    """Get or create the predictor instance"""
    global _predictor
    if _predictor is None:
        _predictor = PropertyPricePredictor()
    return _predictor