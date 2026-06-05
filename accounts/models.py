from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        if not username:
            raise ValueError('Username is required')
        
        email = self.normalize_email(email)
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError('Invalid email format')
        
        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'active')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)
    
    def create_admin(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('status', 'active')
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Profile Image Field
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    
    # ✅ OTP Fields for Forgot Password (MOVED INSIDE User class)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    
    # Role and Status
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    # Django auth requirements
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # Tracking
    last_login = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    USER_ID_FIELD = 'user_id'
    
    class Meta:
        db_table = 'user'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_active_account(self):
        return self.status == 'active' and self.is_active
    
    @property
    def member_since(self):
        """Return formatted member since date"""
        return self.created_at.strftime('%B %d, %Y')
    
    @property
    def member_years(self):
        """Return number of years as member"""
        return (timezone.now().date() - self.created_at.date()).days // 365
    
    def activate(self):
        self.status = 'active'
        self.is_active = True
        self.save()
    
    def deactivate(self):
        self.status = 'inactive'
        self.is_active = False
        self.save()
    
    def update_last_login_info(self, ip_address=None):
        self.last_login = timezone.now()
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['last_login', 'last_login_ip'])
    
    def get_profile_image_url(self, request=None):
        """Get full URL of profile image"""
        if self.profile_image and self.profile_image.name:
            if request:
                return request.build_absolute_uri(self.profile_image.url)
            return self.profile_image.url
        return None


class Admin(models.Model):
    """Legacy admin table - keep for compatibility"""
    admin_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    email = models.EmailField(max_length=100, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin'
        managed = False
        
    def __str__(self):
        return self.username
    
    def set_password(self, raw_password):
        """Hash and set the password"""
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Check if the raw password matches the hashed password"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)
    
    def update_last_login(self):
        """Update last_login timestamp"""
        from django.utils import timezone
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])