# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
import re

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    full_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'full_name', 'password', 'password2', 'phone')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already exists")
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters")
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError("Username contains invalid characters")
        return value

    def validate_email(self, value):
        validate_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    member_since = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    full_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = User
        fields = ('user_id', 'email', 'username', 'full_name', 'phone', 'role', 'is_active', 
                 'created_at', 'last_login', 'member_since', 'profile_image', 'status')
        read_only_fields = ('user_id', 'role', 'is_active', 'created_at', 'last_login', 'status')
    
    def get_member_since(self, obj):
        """Get formatted member since date"""
        if hasattr(obj, 'created_at') and obj.created_at:
            return obj.created_at.strftime('%B %d, %Y')
        elif hasattr(obj, 'date_joined') and obj.date_joined:
            return obj.date_joined.strftime('%B %d, %Y')
        return None
    
    def get_profile_image(self, obj):
        """Get full URL of profile image"""
        if hasattr(obj, 'profile_image') and obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords don't match"})
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({"new_password": "New password must be different from old password"})
        return attrs


class UpdateEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField(required=True)
    
    def validate_new_email(self, value):
        validate_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value


class UpdateUsernameSerializer(serializers.Serializer):
    new_username = serializers.CharField(required=True)
    
    def validate_new_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already exists")
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters")
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError("Username contains invalid characters")
        return value


class ProfileImageSerializer(serializers.Serializer):
    profile_image = serializers.ImageField(required=True)
    
    def validate_profile_image(self, value):
        # Validate file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image size cannot exceed 5MB")
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(f"Unsupported file type. Allowed: {', '.join(allowed_types)}")
        
        return value