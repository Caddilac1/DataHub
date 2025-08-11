import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models, IntegrityError
from django.conf import settings


# ---------- Helper ----------
def generate_custom_id(prefix):
    """Generate a short, unique, non-guessable ID."""
    return f"{prefix.upper()}-{uuid.uuid4().hex[:10]}"


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


# ---------- Custom User ----------
class CustomUser(AbstractUser):
    id = models.CharField(primary_key=True, max_length=20, default=generate_user_id, editable=False)

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent'),
        ('admin', 'Admin'),
    ]

    username = None
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @staticmethod
    def get_by_email(email):
        return CustomUser.objects.filter(email=email).first()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_user_id()
        super().save(*args, **kwargs)


# ---------- Telco ----------
class Telco(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_telco_id, editable=False)
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    is_instock = models.BooleanField(default=True)
    is_out_of_stock = models.BooleanField(default=False)
    is_limited = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @staticmethod
    def get_by_code(code):
        return Telco.objects.filter(code=code).first()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_telco_id()
        super().save(*args, **kwargs)


# ---------- Bundle ----------
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

    class Meta:
        ordering = ['telco__name', 'size_mb']
        unique_together = ('telco', 'size_mb', 'name')

    def __str__(self):
        return f"{self.telco.name} - {self.name} - {self.size_mb}MB"

    @staticmethod
    def get_bundles_for_telco(telco_code):
        return Bundle.objects.filter(telco__code=telco_code).order_by('size_mb')

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_bundle_id()
        try:
            super().save(*args, **kwargs)
        except IntegrityError:
            raise IntegrityError(f"Bundle already exists for {self.telco} with size {self.size_mb}MB.")

    def delete(self, *args, **kwargs):
        raise IntegrityError("Bundle deletion is disabled to maintain data integrity.")


# ---------- Data Bundle Order ----------
class DataBundleOrder(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_order_id, editable=False)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    telco = models.ForeignKey(Telco, on_delete=models.PROTECT)
    bundle = models.ForeignKey(Bundle, on_delete=models.PROTECT)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_order_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} - {self.bundle} - {self.status}"

    @staticmethod
    def get_pending_orders():
        return DataBundleOrder.objects.filter(status='pending')

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_order_id()
        super().save(*args, **kwargs)


# ---------- Payment ----------
class Payment(models.Model):
    id = models.CharField(primary_key=True, max_length=20, default=generate_payment_id, editable=False)

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    order = models.OneToOneField(DataBundleOrder, on_delete=models.PROTECT, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
