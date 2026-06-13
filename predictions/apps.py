# H:\Backend\predictions\apps.py

from django.apps import AppConfig
import sys
import threading
import time

class PredictionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictions'
    
    def ready(self):
        """Pre-load the prediction model when Django starts"""
        
        # Skip during migrations and shell
        if any(arg in sys.argv for arg in ['migrate', 'makemigrations', 'shell', 'test']):
            return
        
        # Start background thread to pre-load model
        def preload_model():
            time.sleep(2)  # Wait for Django to fully start
            try:
                print("\n" + "=" * 60)
                print("🔄 PRE-LOADING PREDICTION MODEL...")
                print("=" * 60)
                
                start_time = time.time()
                from .prediction_service import get_predictor
                predictor = get_predictor()
                load_time = time.time() - start_time
                
                print(f" Model loaded in {load_time:.2f} seconds")
                print(f" Ready for instant predictions!")
                print("=" * 60 + "\n")
            except Exception as e:
                print(f" Warning: Could not pre-load model: {e}")
        
        thread = threading.Thread(target=preload_model)
        thread.daemon = True
        thread.start()