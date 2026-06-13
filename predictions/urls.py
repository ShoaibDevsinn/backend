from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

urlpatterns = [
    # Prediction endpoints - CSRF disabled for API
    path('predict/', csrf_exempt(views.predict_property_price), name='predict'),
    path('predict/save/', csrf_exempt(views.save_prediction), name='save_prediction'),
    
    # User predictions management
    path('predictions/', views.get_user_predictions, name='user_predictions'),
    path('predictions/<int:prediction_id>/', views.get_prediction_detail, name='prediction_detail'),
    path('predictions/<int:prediction_id>/delete/', csrf_exempt(views.delete_prediction), name='delete_prediction'),
    
    # Statistics
    path('predictions/stats/', views.get_prediction_stats, name='prediction_stats'),
]