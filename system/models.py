from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent'),
        ('admin', 'Admin'),
    ]

    username = None  # remove username field
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)  # make sure email is unique
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = ['full_name', 'phone_number']  

    def __str__(self):
        return self.email


class Telco(models.Model):
    name = models.CharField(max_length=50)  # MTN, Telecel, AirtelTigo
    code = models.CharField(max_length=20, unique=True)  # For API calls

    def __str__(self):
        return self.name


class Bundle(models.Model):
    telco = models.ForeignKey(Telco, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # e.g. "1GB"
    size_mb = models.PositiveIntegerField()  # 1024 for 1GB
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price in GHS

    def __str__(self):
        return f"{self.telco.name} - {self.name}"


class DataBundleOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    telco = models.ForeignKey(Telco, on_delete=models.CASCADE)
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_order_id = models.CharField(max_length=100, blank=True, null=True)  # from main system
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} - {self.bundle} - {self.status}"


class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    order = models.OneToOneField(DataBundleOrder, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)  # Paystack reference
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for {self.order} - {self.status}"

