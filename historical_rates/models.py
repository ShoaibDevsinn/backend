from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

MAX_PRICE = Decimal('1000000000.00')  # 10 Crore

class LocationRate(models.Model):
    location_rate_id = models.AutoField(primary_key=True)
    location_name = models.CharField(max_length=100, unique=True)
    area_name = models.CharField(max_length=100)
    city = models.CharField(max_length=50, default='Lahore')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'location_rate'
        ordering = ['location_name']
    
    def __str__(self):
        return f"{self.location_name} - {self.area_name}"
    
    @property
    def years_list(self):
        return list(self.years.values_list('year', flat=True).order_by('-year'))
    
    @property
    def latest_prices(self):
        latest = self.years.order_by('-year').first()
        if latest:
            return {
                'year': latest.year,
                'price_5_marla': latest.price_5_marla,
                'price_10_marla': latest.price_10_marla,
                'price_1_kanal': latest.price_1_kanal,
                'price_2_kanal': latest.price_2_kanal,
            }
        return None
    
    @property
    def year_range(self):
        from django.db.models import Min, Max
        years = self.years.aggregate(min_year=Min('year'), max_year=Max('year'))
        return years


class HistoricalYearRate(models.Model):
    year_rate_id = models.AutoField(primary_key=True)
    location = models.ForeignKey(
        LocationRate, 
        on_delete=models.CASCADE, 
        related_name='years', 
        db_column='location_rate_id'
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    
    price_5_marla = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MaxValueValidator(MAX_PRICE)]
    )
    price_10_marla = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MaxValueValidator(MAX_PRICE)]
    )
    price_1_kanal = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MaxValueValidator(MAX_PRICE)]
    )
    price_2_kanal = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MaxValueValidator(MAX_PRICE)]
    )
    
    per_marla_rate_5 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    per_marla_rate_10 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    per_marla_rate_1k = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    per_marla_rate_2k = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    
    growth_percentage_5 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    growth_percentage_10 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    growth_percentage_1k = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    growth_percentage_2k = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'historical_year_rate'
        unique_together = ['location', 'year']
        ordering = ['-year']
        indexes = [
            models.Index(fields=['location', 'year']),
            models.Index(fields=['year']),
        ]
    
    def __str__(self):
        return f"{self.location.location_name} - {self.year}"
    
    def save(self, *args, **kwargs):
        self._calculate_per_marla_rates()
        self._calculate_growth_percentages()
        super().save(*args, **kwargs)
    
    def _calculate_per_marla_rates(self):
        from decimal import Decimal, ROUND_HALF_UP
        
        calculations = {
            'price_5_marla': ('per_marla_rate_5', Decimal('5')),
            'price_10_marla': ('per_marla_rate_10', Decimal('10')),
            'price_1_kanal': ('per_marla_rate_1k', Decimal('20')),
            'price_2_kanal': ('per_marla_rate_2k', Decimal('40')),
        }
        
        for price_field, (rate_field, divisor) in calculations.items():
            price = getattr(self, price_field)
            if price is not None and price > 0:
                value = (price / divisor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                setattr(self, rate_field, value)
            else:
                setattr(self, rate_field, None)
    
    def _calculate_growth_percentages(self):
        prev_year = HistoricalYearRate.objects.filter(
            location=self.location, 
            year=self.year - 1
        ).first()
        
        if not prev_year:
            self.growth_percentage_5 = None
            self.growth_percentage_10 = None
            self.growth_percentage_1k = None
            self.growth_percentage_2k = None
            return
        
        from decimal import Decimal, ROUND_HALF_UP
        
        calculations = [
            ('price_5_marla', 'growth_percentage_5'),
            ('price_10_marla', 'growth_percentage_10'),
            ('price_1_kanal', 'growth_percentage_1k'),
            ('price_2_kanal', 'growth_percentage_2k'),
        ]
        
        for price_field, growth_field in calculations:
            prev_price = getattr(prev_year, price_field)
            curr_price = getattr(self, price_field)
            
            if (prev_price is not None and prev_price > 0 and 
                curr_price is not None and curr_price > 0):
                growth = ((curr_price - prev_price) / prev_price * Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                setattr(self, growth_field, growth)
            else:
                setattr(self, growth_field, None)


class PriceHistoryLog(models.Model):
    LOG_ACTION_CHOICES = [
        ('location_added', 'Location Added'),
        ('location_updated', 'Location Updated'),
        ('location_deleted', 'Location Deleted'),
        ('year_added', 'Year Added'),
        ('year_updated', 'Year Updated'),
        ('year_deleted', 'Year Deleted'),
        ('price_updated', 'Price Updated'),
        ('bulk_update', 'Bulk Update'),
        ('data_import', 'Data Import'),
        ('data_export', 'Data Export'),
    ]
    
    log_id = models.AutoField(primary_key=True)
    location = models.ForeignKey(
        LocationRate, 
        on_delete=models.CASCADE, 
        db_column='location_rate_id', 
        related_name='logs'
    )
    location_name = models.CharField(max_length=100, blank=True, null=True)
    year = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=50, choices=LOG_ACTION_CHOICES, default='price_updated')
    field_name = models.CharField(max_length=50, blank=True, null=True)
    old_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    new_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    details = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, db_column='changed_by'
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_history_log'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['location', '-changed_at']),
            models.Index(fields=['changed_at']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.location_name or self.location.location_name} - {self.year} - {self.action}"