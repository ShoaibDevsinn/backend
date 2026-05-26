from rest_framework import serializers
from .models import LocationRate, HistoricalYearRate, PriceHistoryLog, MAX_PRICE
from decimal import Decimal


class HistoricalYearRateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)
    plot_sizes = serializers.SerializerMethodField()
    
    class Meta:
        model = HistoricalYearRate
        fields = [
            'year_rate_id', 'year',
            'price_5_marla', 'price_10_marla', 'price_1_kanal', 'price_2_kanal',
            'per_marla_rate_5', 'per_marla_rate_10', 'per_marla_rate_1k', 'per_marla_rate_2k',
            'growth_percentage_5', 'growth_percentage_10', 'growth_percentage_1k', 'growth_percentage_2k',
            'plot_sizes', 'updated_by', 'updated_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'per_marla_rate_5', 'per_marla_rate_10', 'per_marla_rate_1k', 'per_marla_rate_2k',
            'growth_percentage_5', 'growth_percentage_10', 'growth_percentage_1k', 'growth_percentage_2k',
            'created_at', 'updated_at'
        ]
    
    def validate_price_5_marla(self, value):
        if value and value > MAX_PRICE:
            raise serializers.ValidationError(
                f'Price cannot exceed 10 Crore (₹{MAX_PRICE:,.2f})'
            )
        return value
    
    def validate_price_10_marla(self, value):
        if value and value > MAX_PRICE:
            raise serializers.ValidationError(
                f'Price cannot exceed 10 Crore (₹{MAX_PRICE:,.2f})'
            )
        return value
    
    def validate_price_1_kanal(self, value):
        if value and value > MAX_PRICE:
            raise serializers.ValidationError(
                f'Price cannot exceed 10 Crore (₹{MAX_PRICE:,.2f})'
            )
        return value
    
    def validate_price_2_kanal(self, value):
        if value and value > MAX_PRICE:
            raise serializers.ValidationError(
                f'Price cannot exceed 10 Crore (₹{MAX_PRICE:,.2f})'
            )
        return value
    
    def get_plot_sizes(self, obj):
        return {
            '5_marla': {
                'price': str(obj.price_5_marla) if obj.price_5_marla else None,
                'per_marla': str(obj.per_marla_rate_5) if obj.per_marla_rate_5 else None,
                'growth': str(obj.growth_percentage_5) if obj.growth_percentage_5 else None
            },
            '10_marla': {
                'price': str(obj.price_10_marla) if obj.price_10_marla else None,
                'per_marla': str(obj.per_marla_rate_10) if obj.per_marla_rate_10 else None,
                'growth': str(obj.growth_percentage_10) if obj.growth_percentage_10 else None
            },
            '1_kanal': {
                'price': str(obj.price_1_kanal) if obj.price_1_kanal else None,
                'per_marla': str(obj.per_marla_rate_1k) if obj.per_marla_rate_1k else None,
                'growth': str(obj.growth_percentage_1k) if obj.growth_percentage_1k else None
            },
            '2_kanal': {
                'price': str(obj.price_2_kanal) if obj.price_2_kanal else None,
                'per_marla': str(obj.per_marla_rate_2k) if obj.per_marla_rate_2k else None,
                'growth': str(obj.growth_percentage_2k) if obj.growth_percentage_2k else None
            }
        }


class LocationRateSerializer(serializers.ModelSerializer):
    years = HistoricalYearRateSerializer(many=True, read_only=True)
    years_count = serializers.SerializerMethodField()
    latest_year = serializers.SerializerMethodField()
    available_years = serializers.SerializerMethodField()
    year_range = serializers.SerializerMethodField()
    
    class Meta:
        model = LocationRate
        fields = [
            'location_rate_id', 'location_name', 'area_name', 'city',
            'description', 'years', 'years_count', 'latest_year',
            'available_years', 'year_range', 'created_at', 'updated_at'
        ]
    
    def get_years_count(self, obj):
        return obj.years.count()
    
    def get_latest_year(self, obj):
        latest = obj.years.order_by('-year').first()
        return latest.year if latest else None
    
    def get_available_years(self, obj):
        return list(obj.years.values_list('year', flat=True).order_by('-year'))
    
    def get_year_range(self, obj):
        range_data = obj.year_range
        return {
            'min_year': range_data.get('min_year'),
            'max_year': range_data.get('max_year')
        }


class LocationRateListSerializer(serializers.ModelSerializer):
    years_count = serializers.SerializerMethodField()
    latest_prices = serializers.SerializerMethodField()
    available_years = serializers.SerializerMethodField()
    year_range = serializers.SerializerMethodField()
    
    class Meta:
        model = LocationRate
        fields = [
            'location_rate_id', 'location_name', 'area_name', 'city',
            'years_count', 'latest_prices', 'available_years', 
            'year_range', 'created_at'
        ]
    
    def get_years_count(self, obj):
        return obj.years.count()
    
    def get_latest_prices(self, obj):
        latest = obj.years.order_by('-year').first()
        if latest:
            return {
                'year': latest.year,
                'price_5_marla': str(latest.price_5_marla) if latest.price_5_marla else None,
                'price_10_marla': str(latest.price_10_marla) if latest.price_10_marla else None,
                'price_1_kanal': str(latest.price_1_kanal) if latest.price_1_kanal else None,
                'price_2_kanal': str(latest.price_2_kanal) if latest.price_2_kanal else None,
            }
        return None
    
    def get_available_years(self, obj):
        return list(obj.years.values_list('year', flat=True).order_by('-year'))
    
    def get_year_range(self, obj):
        range_data = obj.year_range
        return {
            'min_year': range_data.get('min_year'),
            'max_year': range_data.get('max_year')
        }


class CreateLocationSerializer(serializers.ModelSerializer):
    initial_year = serializers.IntegerField(write_only=True, required=True)
    price_5_marla = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0,
        max_value=MAX_PRICE
    )
    price_10_marla = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0,
        max_value=MAX_PRICE
    )
    price_1_kanal = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0,
        max_value=MAX_PRICE
    )
    price_2_kanal = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0,
        max_value=MAX_PRICE
    )
    
    class Meta:
        model = LocationRate
        fields = [
            'location_name', 'area_name', 'city', 'description',
            'initial_year', 'price_5_marla', 'price_10_marla',
            'price_1_kanal', 'price_2_kanal'
        ]
    
    def validate_location_name(self, value):
        if LocationRate.objects.filter(location_name__iexact=value).exists():
            raise serializers.ValidationError("Location name already exists")
        return value
    
    def validate_initial_year(self, value):
        if value < 2000 or value > 2100:
            raise serializers.ValidationError("Year must be between 2000 and 2100")
        return value
    
    def create(self, validated_data):
        initial_year = validated_data.pop('initial_year')
        prices = {
            'price_5_marla': validated_data.pop('price_5_marla', 0),
            'price_10_marla': validated_data.pop('price_10_marla', 0),
            'price_1_kanal': validated_data.pop('price_1_kanal', 0),
            'price_2_kanal': validated_data.pop('price_2_kanal', 0),
        }
        
        location = LocationRate.objects.create(**validated_data)
        
        HistoricalYearRate.objects.create(
            location=location,
            year=initial_year,
            **prices,
            updated_by=self.context['request'].user
        )
        
        return location


class AddYearSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=True)
    price_5_marla = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0,
        max_value=MAX_PRICE
    )
    price_10_marla = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0,
        max_value=MAX_PRICE
    )
    price_1_kanal = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0,
        max_value=MAX_PRICE
    )
    price_2_kanal = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, default=0,
        max_value=MAX_PRICE
    )
    
    def validate_year(self, value):
        if value < 2000 or value > 2100:
            raise serializers.ValidationError("Year must be between 2000 and 2100")
        return value


class BulkYearRateUpdateSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=True)
    price_5_marla = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True,
        max_value=MAX_PRICE
    )
    price_10_marla = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True,
        max_value=MAX_PRICE
    )
    price_1_kanal = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True,
        max_value=MAX_PRICE
    )
    price_2_kanal = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True,
        max_value=MAX_PRICE
    )


class PriceHistoryLogSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.location_name', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = PriceHistoryLog
        fields = [
            'log_id', 'location_name', 'year', 'action',
            'field_name', 'old_value', 'new_value', 'details',
            'changed_by', 'changed_by_name', 'changed_at'
        ]


class YearComparisonSerializer(serializers.Serializer):
    """For comparing two years"""
    year1 = serializers.IntegerField(required=True)
    year2 = serializers.IntegerField(required=True)
    plot_type = serializers.ChoiceField(
        choices=['5_marla', '10_marla', '1_kanal', '2_kanal'],
        required=False
    )