from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Fields to display in the list view
    list_display = ('email', 'full_name', 'phone_number', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')

    # Fields for the add/edit user forms in admin
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number')}),
        ('Roles & Permissions', {'fields': ('role', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fields for the user creation form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'full_name',
                'phone_number',
                'role',
                'password1',
                'password2',
                'is_staff',
                'is_superuser',
                'is_active'
            ),
        }),
    )

    search_fields = ('username', 'email', 'full_name', 'phone_number')
    ordering = ('email',)


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