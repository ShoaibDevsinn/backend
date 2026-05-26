from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'email', 'full_name', 'phone',
            'role', 'role_display', 'status', 'status_display',
            'last_login', 'last_login_ip', 'created_at', 'is_active'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for single user details"""
    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'email', 'full_name', 'phone',
            'role', 'status', 'last_login', 'last_login_ip',
            'created_at', 'updated_at', 'is_active', 'is_staff', 'is_superuser'
        ]
        read_only_fields = ['user_id', 'created_at', 'updated_at', 'last_login', 'last_login_ip']


class CreateUserSerializer(serializers.ModelSerializer):
    """Serializer for creating new user/admin"""
    # password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'phone', 'password', 'confirm_password', 'role'
        ]
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)
        
        # Set is_staff and is_superuser for admin role
        if user.role == 'admin':
            user.is_staff = True
        
        user.save()
        return user


class UpdateUserSerializer(serializers.ModelSerializer):
    """Serializer for updating user"""
    class Meta:
        model = User
        fields = ['full_name', 'phone', 'role', 'status']
    
    def update(self, instance, validated_data):
        # Update role
        if 'role' in validated_data:
            instance.role = validated_data['role']
            instance.is_staff = (validated_data['role'] == 'admin')
        
        # Update other fields
        for attr, value in validated_data.items():
            if attr != 'role':
                setattr(instance, attr, value)
        
        instance.save()
        return instance


class ChangeUserStatusSerializer(serializers.Serializer):
    """Serializer for activating/deactivating users"""
    status = serializers.ChoiceField(choices=['active', 'inactive', 'suspended'])
    
    def validate_status(self, value):
        if value not in ['active', 'inactive', 'suspended']:
            raise serializers.ValidationError("Invalid status")
        return value


class ChangeUserRoleSerializer(serializers.Serializer):
    """Serializer for changing user role"""
    role = serializers.ChoiceField(choices=['admin', 'user'])
    
    def validate_role(self, value):
        if value not in ['admin', 'user']:
            raise serializers.ValidationError("Invalid role")
        return value


class UserFilterSerializer(serializers.Serializer):
    """Serializer for filter parameters"""
    search = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=['admin', 'user', 'all'], required=False, default='all')
    status = serializers.ChoiceField(choices=['active', 'inactive', 'suspended', 'all'], required=False, default='all')
    sort_by = serializers.CharField(required=False, default='-created_at')