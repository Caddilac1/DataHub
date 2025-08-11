from django.db import models

# Create your models here.
import uuid
import secrets
import string
from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models, IntegrityError, transaction
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password


# ---------- Helper Functions ----------
def generate_custom_id(prefix):
    """Generate a short, unique, non-guessable ID."""
    return f"{prefix.upper()}-{uuid.uuid4().hex[:10]}"

def generate_secure_otp(length=6):
    """Generate a cryptographically secure OTP."""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp):
    """Hash OTP for secure storage."""
    return make_password(otp)

def verify_otp(otp, hashed_otp):
    """Verify OTP against hashed version."""
    return check_password(otp, hashed_otp)


# ---------- ID Generators ----------
def generate_user_id():
    return generate_custom_id("USR")

def generate_telco_id():
    return generate_custom_id("TEL")

def generate_bundle_id():
    return generate_custom_id("BND")

def generate_order_id():
    return generate_custom_id("ORD")

def generate_payment_id():
    return generate_custom_id("PAY")

def generate_reference_id():
    return generate_custom_id("REF")

def generate_otp_id():
    return generate_custom_id("OTP")

def generate_audit_id():
    return generate_custom_id("AUD")


# ---------- Custom User Model ----------
class CustomUser(AbstractUser):
    id = models.CharField(primary_key=True, max_length=20, default=generate_user_id, editable=False)

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent'),
        ('admin', 'Admin'),
    ]

    ACCOUNT_STATUS_CHOICES = [
        ('pending_verification', 'Pending Email Verification'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('deactivated', 'Deactivated'),
    ]

    username = None
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    account_status = models.CharField(
        max_length=30, 
        choices=ACCOUNT_STATUS_CHOICES, 
        default='pending_verification'
    )
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    last_login_attempt = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number']

    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['account_status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def is_account_locked(self):
        """Check if account is temporarily locked due to failed login attempts."""
        if self.account_locked_until and timezone.now() < self.account_locked_until:
            return True
        return False

    @property
    def can_login(self):
        """Check if user can attempt login."""
        return (
            self.account_status == 'active' and 
            self.email_verified and 
            not self.is_account_locked
        )

    def lock_account_temporarily(self, lock_duration_minutes=30):
        """Lock account temporarily after multiple failed attempts."""
        self.account_locked_until = timezone.now() + timedelta(minutes=lock_duration_minutes)
        self.save(update_fields=['account_locked_until'])

    def unlock_account(self):
        """Unlock account and reset failed attempts."""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])

    def increment_failed_login(self):
        """Increment failed login attempts and lock if necessary."""
        self.failed_login_attempts += 1
        self.last_login_attempt = timezone.now()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account_temporarily()
        
        self.save(update_fields=['failed_login_attempts', 'last_login_attempt'])

    def reset_failed_login_attempts(self):
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.last_login_attempt = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'last_login_attempt'])

    def verify_email(self):
        """Mark email as verified and activate account."""
        with transaction.atomic():
            self.email_verified = True
            self.email_verified_at = timezone.now()
            self.account_status = 'active'
            self.is_active = True  # Django's built-in field
            self.save(update_fields=[
                'email_verified', 
                'email_verified_at', 
                'account_status', 
                'is_active'
            ])

    @staticmethod
    def get_by_email(email):
        """Get user by email address."""
        return CustomUser.objects.filter(email=email).first()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_user_id()
        
        # Set is_active based on account_status for Django compatibility
        self.is_active = self.account_status == 'active'
        
        super().save(*args, **kwargs)

    def clean(self):
        """Custom validation for the model."""
        super().clean()
        
        # Validate phone number format (basic validation)
        if self.phone_number and not self.phone_number.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValidationError({'phone_number': 'Invalid phone number format'})


# ---------- OTP Model ----------
class OTP(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_otp_id, editable=False)
    
    OTP_TYPE_CHOICES = [
        ('email_verification', 'Email Verification'),
        ('login_verification', 'Login Verification'),
        ('password_reset', 'Password Reset'),
        ('phone_verification', 'Phone Verification'),
    ]
    
    OTP_STATUS_CHOICES = [
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('invalidated', 'Invalidated'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otps')
    otp_type = models.CharField(max_length=20, choices=OTP_TYPE_CHOICES)
    hashed_code = models.CharField(max_length=128)  # Store hashed OTP for security
    status = models.CharField(max_length=15, choices=OTP_STATUS_CHOICES, default='active')
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'otp_type', 'status']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"OTP for {self.user.email} - {self.otp_type} - {self.status}"

    @property
    def is_expired(self):
        """Check if OTP has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if OTP is valid for use."""
        return (
            self.status == 'active' and 
            not self.is_expired and 
            self.attempts < self.max_attempts
        )

    @classmethod
    def generate_otp(cls, user, otp_type, validity_minutes=10, ip_address=None, user_agent=None):
        """Generate a new OTP for a user."""
        with transaction.atomic():
            # Invalidate previous active OTPs of the same type
            cls.objects.filter(
                user=user, 
                otp_type=otp_type, 
                status='active'
            ).update(status='invalidated')
            
            # Generate new OTP
            code = generate_secure_otp()
            hashed_code = hash_otp(code)
            expires_at = timezone.now() + timedelta(minutes=validity_minutes)
            
            otp_instance = cls.objects.create(
                user=user,
                otp_type=otp_type,
                hashed_code=hashed_code,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return otp_instance, code  # Return instance and plain code for sending

    def verify_code(self, code):
        """Verify the provided OTP code."""
        self.attempts += 1
        self.save(update_fields=['attempts', 'updated_at'])
        
        if not self.is_valid:
            if self.is_expired:
                self.status = 'expired'
                self.save(update_fields=['status'])
            elif self.attempts >= self.max_attempts:
                self.status = 'invalidated'
                self.save(update_fields=['status'])
            return False
        
        if verify_otp(code, self.hashed_code):
            self.status = 'used'
            self.used_at = timezone.now()
            self.save(update_fields=['status', 'used_at'])
            return True
        
        return False

    @classmethod
    def cleanup_expired_otps(cls):
        """Clean up expired and old OTPs - should be run as a periodic task."""
        cutoff_time = timezone.now() - timedelta(days=7)  # Keep records for 7 days
        cls.objects.filter(created_at__lt=cutoff_time).delete()
        
        # Mark expired OTPs
        cls.objects.filter(
            expires_at__lt=timezone.now(),
            status='active'
        ).update(status='expired')

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_otp_id()
        super().save(*args, **kwargs)


# ---------- Existing Models (Enhanced with Security) ----------
class Telco(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_telco_id, editable=False)
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    @staticmethod
    def get_by_code(code):
        return Telco.objects.filter(code=code, is_active=True).first()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_telco_id()
        super().save(*args, **kwargs)


class Bundle(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_bundle_id, editable=False)

    NAME_CHOICES = [
        ('mtnup2u', 'MTNUP2U'),
        ('telecel', 'Telecel'),
        ('atishare', 'AT-iShare'),
    ]

    telco = models.ForeignKey(Telco, on_delete=models.PROTECT)
    name = models.CharField(max_length=50, choices=NAME_CHOICES)
    size_mb = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_instock = models.BooleanField(default=True)
    is_out_of_stock = models.BooleanField(default=False)
    is_limited = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['telco__name', 'size_mb']
        unique_together = ('telco', 'size_mb', 'name')
        indexes = [
            models.Index(fields=['telco', 'is_active']),
            models.Index(fields=['is_instock']),
        ]

    def __str__(self):
        return f"{self.telco.name} - {self.name} - {self.size_mb}MB"

    @staticmethod
    def get_bundles_for_telco(telco_code):
        return Bundle.objects.filter(
            telco__code=telco_code, 
            telco__is_active=True,
            is_active=True
        ).order_by('size_mb')

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_bundle_id()
        try:
            super().save(*args, **kwargs)
        except IntegrityError:
            raise IntegrityError(f"Bundle already exists for {self.telco} with size {self.size_mb}MB.")

    def delete(self, *args, **kwargs):
        # Soft delete instead of hard delete
        self.is_active = False
        self.save(update_fields=['is_active'])


class DataBundleOrder(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_order_id, editable=False)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    telco = models.ForeignKey(Telco, on_delete=models.PROTECT)
    bundle = models.ForeignKey(Bundle, on_delete=models.PROTECT)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_order_id = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['phone_number']),
        ]

    def __str__(self):
        return f"{self.phone_number} - {self.bundle} - {self.status}"

    @staticmethod
    def get_pending_orders():
        return DataBundleOrder.objects.filter(status='pending')

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_order_id()
        super().save(*args, **kwargs)


class Payment(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_payment_id, editable=False)

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    order = models.OneToOneField(DataBundleOrder, on_delete=models.PROTECT, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    paid_at = models.DateTimeField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Payment for {self.order} - {self.status}"

    @staticmethod
    def get_by_reference(reference):
        return Payment.objects.filter(reference=reference).first()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_payment_id()
        if not self.reference:
            self.reference = generate_reference_id()
        super().save(*args, **kwargs)


# ---------- Audit Log Model (Optional but Recommended) ----------
class AuditLog(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_audit_id, editable=False)
    
    ACTION_CHOICES = [
        ('user_created', 'User Created'),
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('email_verified', 'Email Verified'),
        ('otp_generated', 'OTP Generated'),
        ('otp_verified', 'OTP Verified'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        ('order_created', 'Order Created'),
        ('payment_made', 'Payment Made'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.action} - {self.user} - {self.created_at}"