from rest_framework import serializers
from .models import Admin

class AdminSignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50, required=True)
    email = serializers.EmailField(max_length=100, required=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    password = serializers.CharField(max_length=255, required=True, write_only=True)
    confirm_password = serializers.CharField(max_length=255, required=True, write_only=True)
    
    def validate_username(self, value):
        if Admin.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate_email(self, value):
        if Admin.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if len(data['password']) < 6:
            raise serializers.ValidationError({"password": "Password must be at least 6 characters."})
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        admin = Admin(
            username=validated_data['username'],
            email=validated_data['email'],
            phone=validated_data.get('phone', '')
        )
        admin.set_password(validated_data['password'])
        admin.save()
        return admin


class AdminLoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField(max_length=100, required=True)
    password = serializers.CharField(max_length=255, required=True, write_only=True)
    
    def validate(self, data):
        username_or_email = data.get('username_or_email')
        password = data.get('password')
        
        try:
            if '@' in username_or_email:
                admin = Admin.objects.get(email=username_or_email)
            else:
                admin = Admin.objects.get(username=username_or_email)
        except Admin.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")
        
        if not admin.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")
        
        admin.update_last_login()
        data['admin'] = admin
        return data


class AdminProfileSerializer(serializers.ModelSerializer):
    member_since = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Admin
        fields = [
            'admin_id', 'username', 'email', 'phone',
            'full_name', 'address', 'bio', 'profile_image_url',
            'last_login', 'created_at', 'member_since'
        ]
        read_only_fields = ['admin_id', 'last_login', 'created_at', 'member_since']
    
    def get_member_since(self, obj):
        if obj.created_at:
            return obj.created_at.strftime('%B %Y')
        return None
    
    def get_full_name(self, obj):
        return getattr(obj, 'full_name', '') or ''
    
    def get_address(self, obj):
        return getattr(obj, 'address', '') or ''
    
    def get_bio(self, obj):
        return getattr(obj, 'bio', '') or ''
    
    def get_profile_image_url(self, obj):
        img = getattr(obj, 'profile_image', None)
        if img:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/media/{img}')
            return f'/media/{img}'
        return None


class AdminProfileUpdateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    class Meta:
        model = Admin
        fields = ['full_name', 'phone', 'address', 'bio', 'profile_image']
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AdminChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=255, required=True, write_only=True)
    new_password = serializers.CharField(max_length=255, required=True, write_only=True)
    confirm_password = serializers.CharField(max_length=255, required=True, write_only=True)
    
    def validate_old_password(self, value):
        admin = self.context.get('admin')
        if not admin.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match."})
        if len(data['new_password']) < 6:
            raise serializers.ValidationError({"new_password": "Password must be at least 6 characters."})
        return data
    
    def save(self, admin):
        admin.set_password(self.validated_data['new_password'])
        admin.save()
        return admin