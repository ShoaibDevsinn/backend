# H:\Backend\predictions\urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Prediction endpoints
    path('predict/', views.predict_property_price, name='predict'),
    path('predict/save/', views.save_prediction, name='save_prediction'),
    
    # User predictions management
    path('predictions/', views.get_user_predictions, name='user_predictions'),
    path('predictions/<int:prediction_id>/', views.get_prediction_detail, name='prediction_detail'),
    path('predictions/<int:prediction_id>/delete/', views.delete_prediction, name='delete_prediction'),
    
    # Statistics
    path('predictions/stats/', views.get_prediction_stats, name='prediction_stats'),
]