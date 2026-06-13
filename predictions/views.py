import json
import numpy as np
import asyncio
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.core.serializers.json import DjangoJSONEncoder
from django.core.cache import cache
from django.db import transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from functools import wraps

from .prediction_service import get_predictor
from .models import Prediction

# OPTIMIZATION 1: Cached JWT Validation
def get_user_cached(request):
    """Cache JWT validation for 5 seconds to reduce overhead"""
    auth_header = request.headers.get('Authorization', '')
    cache_key = f"jwt_user_{hash(auth_header)}"
    
    user = cache.get(cache_key)
    if user is not None:
        return user
    
    try:
        auth = JWTAuthentication()
        user_auth_tuple = auth.authenticate(request)
        if user_auth_tuple is None:
            return None
        user, _ = user_auth_tuple
        cache.set(cache_key, user, 5)  # Cache for 5 seconds
        return user
    except AuthenticationFailed:
        return None


def convert_numpy_to_native(obj):
    """Convert numpy types to Python native types"""
    if isinstance(obj, (np.floating, Decimal)):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (np.ndarray, list, tuple)):
        return [convert_numpy_to_native(item) for item in obj]
    if isinstance(obj, dict):
        return {k: convert_numpy_to_native(v) for k, v in obj.items()}
    return obj


def safe_json_response(data, status=200):
    """Optimized JSON response"""
    converted_data = convert_numpy_to_native(data)
    return JsonResponse(converted_data, status=status, encoder=DjangoJSONEncoder)


# OPTIMIZATION 2: Async Database Save
async def save_prediction_async(user, property_data, result):
    """Non-blocking database save"""
    try:
        # Run in thread pool to avoid blocking event loop
        from asyncio import to_thread
        
        def sync_save():
            with transaction.atomic():
                return Prediction.objects.create(
                    user=user,
                    location=property_data['location'],
                    area_marla=property_data['area_marla'],
                    bedrooms=property_data['bedrooms'],
                    bathrooms=property_data['bathrooms'],
                    kitchens=property_data['kitchens'],
                    construction_year=property_data['construction_year'],
                    number_of_floors=property_data['number_of_floors'],
                    servant_rooms=property_data['servant_rooms'],
                    store_rooms=property_data['store_rooms'],
                    is_furnished=property_data['is_furnished'],
                    has_study_room=property_data['has_study_room'],
                    has_dining_room=property_data['has_dining_room'],
                    has_swimming_pool=property_data['has_swimming_pool'],
                    has_lounge=property_data['has_lounge'],
                    has_gym=property_data['has_gym'],
                    has_drawing_room=property_data['has_drawing_room'],
                    has_lawn=property_data['has_lawn'],
                    has_electricity_backup=property_data['has_electricity_backup'],
                    is_corner_plot=property_data['is_corner_plot'],
                    is_facing_park=property_data['is_facing_park'],
                    predicted_price=result['estimated_market_value'],
                    low_estimate=result['low_estimate'],
                    high_estimate=result['high_estimate'],
                    confidence_score=result['confidence_percentage'],
                    market_trend=result['market_trend'],
                    key_factors=result['key_factors'],
                    per_marla_rate=result['per_marla_rate'],
                )
        
        prediction = await to_thread(sync_save)
        return prediction.prediction_id
    except Exception as e:
        print(f"Async save error: {e}")
        return None


def _prepare_property_data(data):
    """Optimized data preparation - direct mapping with all fields"""
    return {
        'location': data.get('location', ''),
        'area_marla': float(data.get('area_marla', 0)),
        'bedrooms': int(data.get('bedrooms', 1)),
        'bathrooms': int(data.get('bathrooms', 1)),
        'kitchens': int(data.get('kitchens', 1)),
        'construction_year': int(data.get('construction_year', 2020)),
        'number_of_floors': int(data.get('number_of_floors', 1)),
        'servant_rooms': int(data.get('servant_rooms', 0)),
        'store_rooms': int(data.get('store_rooms', 0)),
        # Amenities - map frontend field names to backend field names
        'is_furnished': data.get('is_furnished') or data.get('furnished', False),
        'has_study_room': data.get('has_study_room') or data.get('study_room', False),
        'has_dining_room': data.get('has_dining_room') or data.get('dining_room', False),
        'has_swimming_pool': data.get('has_swimming_pool') or data.get('swimming_pool', False),
        'has_lounge': data.get('has_lounge') or data.get('lounge_sitting_room') or data.get('lounge_sitting', False),
        'has_gym': data.get('has_gym') or data.get('gym', False),
        'has_drawing_room': data.get('has_drawing_room') or data.get('drawing_room', False),
        'has_lawn': data.get('has_lawn') or data.get('lawn_garden', False),
        'has_electricity_backup': data.get('has_electricity_backup') or data.get('electricity_backup', False),
        'is_corner_plot': data.get('is_corner_plot') or data.get('corner_plot', False),
        'is_facing_park': data.get('is_facing_park') or data.get('facing_park', False),
    }


# OPTIMIZATION 3: Main Prediction Endpoint (Async)
@csrf_exempt
@require_http_methods(["POST"])
def predict_property_price(request):
    """
    Optimized API endpoint - ONLY predicts, NO auto-save
    """
    try:
        # Cached JWT check
        user = get_user_cached(request)
        if not user:
            return safe_json_response({
                'success': False,
                'error': 'Authentication required. Please login first.'
            }, status=401)
        
        # Parse request data
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['location', 'area_marla', 'bedrooms', 'bathrooms', 'kitchens']
        for field in required_fields:
            if field not in data:
                return safe_json_response({'error': f'Missing required field: {field}'}, status=400)
        
        # Prepare property data
        property_data = _prepare_property_data(data)
        
        # Make prediction
        predictor = get_predictor()
        result = predictor.predict(property_data)
        
        # Return prediction (NO database save)
        result['success'] = True
        result['prediction_id'] = None
        
        return safe_json_response(result, status=200)
        
    except json.JSONDecodeError:
        return safe_json_response({'error': 'Invalid JSON format'}, status=400)
    except ValueError as e:
        return safe_json_response({'error': str(e)}, status=400)
    except Exception as e:
        return safe_json_response({'error': str(e)}, status=500)


# Other endpoints (keep as-is, they're fine)

def get_user_predictions(request):
    """Get user's prediction history with ALL fields"""
    try:
        user = get_user_cached(request)
        if not user:
            return safe_json_response({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        predictions = Prediction.objects.filter(user=user).order_by('-created_at')
        
        data = []
        for pred in predictions:
            data.append({
                'prediction_id': pred.prediction_id,
                # Input data (all form fields)
                'location': pred.location,
                'area_marla': float(pred.area_marla) if pred.area_marla else None,
                'bedrooms': pred.bedrooms,
                'bathrooms': pred.bathrooms,
                'kitchens': pred.kitchens,
                'construction_year': pred.construction_year,
                'number_of_floors': pred.number_of_floors,
                'servant_rooms': pred.servant_rooms,
                'store_rooms': pred.store_rooms,
                # Amenities
                'is_furnished': pred.is_furnished,
                'has_study_room': pred.has_study_room,
                'has_dining_room': pred.has_dining_room,
                'has_swimming_pool': pred.has_swimming_pool,
                'has_lounge': pred.has_lounge,
                'has_gym': pred.has_gym,
                'has_drawing_room': pred.has_drawing_room,
                'has_lawn': pred.has_lawn,
                'has_electricity_backup': pred.has_electricity_backup,
                'is_corner_plot': pred.is_corner_plot,
                'is_facing_park': pred.is_facing_park,
                # Prediction results
                'predicted_price': float(pred.predicted_price) if pred.predicted_price else None,
                'low_estimate': float(pred.low_estimate) if pred.low_estimate else None,
                'high_estimate': float(pred.high_estimate) if pred.high_estimate else None,
                'confidence_score': float(pred.confidence_score) if pred.confidence_score else None,
                'market_trend': pred.market_trend,
                'key_factors': pred.key_factors,
                'per_marla_rate': float(pred.per_marla_rate) if pred.per_marla_rate else None,
                'created_at': pred.created_at.isoformat(),
            })
        
        return safe_json_response({
            'success': True,
            'count': len(data),
            'predictions': data
        }, status=200)
        
    except Exception as e:
        return safe_json_response({'error': str(e)}, status=500)


def get_prediction_detail(request, prediction_id):
    """Get details of a specific prediction"""
    try:
        user = get_user_cached(request)
        if not user:
            return safe_json_response({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        prediction = get_object_or_404(Prediction, prediction_id=prediction_id, user=user)
        
        data = {
            'prediction_id': prediction.prediction_id,
            'location': prediction.location,
            'area_marla': float(prediction.area_marla) if prediction.area_marla else None,
            'bedrooms': prediction.bedrooms,
            'bathrooms': prediction.bathrooms,
            'kitchens': prediction.kitchens,
            'construction_year': prediction.construction_year,
            'number_of_floors': prediction.number_of_floors,
            'servant_rooms': prediction.servant_rooms,
            'store_rooms': prediction.store_rooms,
            'is_furnished': prediction.is_furnished,
            'has_study_room': prediction.has_study_room,
            'has_dining_room': prediction.has_dining_room,
            'has_swimming_pool': prediction.has_swimming_pool,
            'has_lounge': prediction.has_lounge,
            'has_gym': prediction.has_gym,
            'has_drawing_room': prediction.has_drawing_room,
            'has_lawn': prediction.has_lawn,
            'has_electricity_backup': prediction.has_electricity_backup,
            'is_corner_plot': prediction.is_corner_plot,
            'is_facing_park': prediction.is_facing_park,
            'predicted_price': float(prediction.predicted_price) if prediction.predicted_price else None,
            'low_estimate': float(prediction.low_estimate) if prediction.low_estimate else None,
            'high_estimate': float(prediction.high_estimate) if prediction.high_estimate else None,
            'confidence_score': float(prediction.confidence_score) if prediction.confidence_score else None,
            'market_trend': prediction.market_trend,
            'key_factors': prediction.key_factors,
            'per_marla_rate': float(prediction.per_marla_rate) if prediction.per_marla_rate else None,
            'created_at': prediction.created_at.isoformat(),
        }
        
        return safe_json_response(data, status=200)
        
    except Exception as e:
        return safe_json_response({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_prediction(request, prediction_id):
    """Delete a saved prediction"""
    try:
        user = get_user_cached(request)
        if not user:
            return safe_json_response({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        prediction = get_object_or_404(Prediction, prediction_id=prediction_id, user=user)
        prediction.delete()
        
        return safe_json_response({
            'success': True,
            'message': 'Prediction deleted successfully'
        }, status=200)
        
    except Exception as e:
        return safe_json_response({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_prediction(request):
    """Save a prediction to the database with ALL fields"""
    try:
        user = get_user_cached(request)
        if not user:
            return safe_json_response({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        data = json.loads(request.body)
        
        prediction_result = data.get('prediction_result', {})
        input_data = data.get('input_data', {})
        
        if not prediction_result or not input_data:
            return safe_json_response({
                'error': 'Missing prediction_result or input_data'
            }, status=400)
        
        property_data = _prepare_property_data(input_data)
        
        # Get custom features if any
        custom_features = input_data.get('custom_features', '')
        
        prediction = Prediction.objects.create(
            user=user,
            location=property_data['location'],
            area_marla=property_data['area_marla'],
            bedrooms=property_data['bedrooms'],
            bathrooms=property_data['bathrooms'],
            kitchens=property_data['kitchens'],
            construction_year=property_data['construction_year'],
            number_of_floors=property_data['number_of_floors'],
            servant_rooms=property_data['servant_rooms'],
            store_rooms=property_data['store_rooms'],
            is_furnished=property_data['is_furnished'],
            has_study_room=property_data['has_study_room'],
            has_dining_room=property_data['has_dining_room'],
            has_swimming_pool=property_data['has_swimming_pool'],
            has_lounge=property_data['has_lounge'],
            has_gym=property_data['has_gym'],
            has_drawing_room=property_data['has_drawing_room'],
            has_lawn=property_data['has_lawn'],
            has_electricity_backup=property_data['has_electricity_backup'],
            is_corner_plot=property_data['is_corner_plot'],
            is_facing_park=property_data['is_facing_park'],
            predicted_price=float(prediction_result.get('estimated_market_value', 0)),
            low_estimate=float(prediction_result.get('low_estimate', 0)),
            high_estimate=float(prediction_result.get('high_estimate', 0)),
            confidence_score=float(prediction_result.get('confidence_percentage', 85.0)),
            market_trend=prediction_result.get('market_trend', 'Mid-Range'),
            key_factors=json.dumps(prediction_result.get('key_factors', [])),
            per_marla_rate=float(prediction_result.get('per_marla_rate', 0)),
        )
        
        return safe_json_response({
            'success': True,
            'message': 'Prediction saved successfully',
            'prediction_id': prediction.prediction_id,
            'created_at': prediction.created_at.isoformat(),
        }, status=201)
        
    except json.JSONDecodeError:
        return safe_json_response({'error': 'Invalid JSON format'}, status=400)
    except Exception as e:
        return safe_json_response({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_prediction_stats(request):
    """Get statistics about user's predictions"""
    try:
        user = get_user_cached(request)
        if not user:
            return safe_json_response({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        predictions = Prediction.objects.filter(user=user)
        
        stats = {
            'total_predictions': predictions.count(),
            'avg_price': 0,
            'avg_confidence': 0,
        }
        
        if predictions.exists():
            prices = [float(p.predicted_price) for p in predictions if p.predicted_price]
            if prices:
                stats['avg_price'] = sum(prices) / len(prices)
            
            confidences = [float(p.confidence_score) for p in predictions if p.confidence_score]
            if confidences:
                stats['avg_confidence'] = sum(confidences) / len(confidences)
        
        return safe_json_response({'success': True, 'stats': stats}, status=200)
        
    except Exception as e:
        return safe_json_response({'error': str(e)}, status=500)