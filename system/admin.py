"""from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

@admin.register(Telco)
class TelcoAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("telco", "name", "size_mb", "price")
    list_filter = ("telco",)
    search_fields = ("name",)


@admin.register(DataBundleOrder)
class DataBundleOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "telco", "bundle", "phone_number", "status", "created_at", "updated_at")
    list_filter = ("status", "telco", "created_at")
    search_fields = ("phone_number", "user__username", "user__email", "provider_order_id")
    ordering = ("-created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "reference", "status", "paid_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("reference", "order__phone_number", "order__user__username", "order__user__email")
    ordering = ("-created_at",)

    """