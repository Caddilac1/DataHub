from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
import csv
import json
from datetime import timedelta
from django.contrib.admin.models import LogEntry

from .models import (
    CustomUser,
    OTP,
    Telco,
    Bundle,
    DataBundleOrder,
    Payment,
    AuditLog
)
from .signals import set_request_context, log_custom_action


# --- General Admin Configuration ---
@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ('user', 'content_type', 'action_flag')
    search_fields = ('object_repr', 'change_message')


# --- Custom Filters ---
class AccountStatusFilter(SimpleListFilter):
    title = 'Account Status'
    parameter_name = 'account_status'

    def lookups(self, request, model_admin):
        return CustomUser.ACCOUNT_STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(account_status=self.value())
        return queryset


class EmailVerifiedFilter(SimpleListFilter):
    title = 'Email Verification'
    parameter_name = 'email_verified'

    def lookups(self, request, model_admin):
        return (
            ('verified', 'Verified'),
            ('unverified', 'Unverified'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(email_verified=True)
        elif self.value() == 'unverified':
            return queryset.filter(email_verified=False)
        return queryset


class RecentActivityFilter(SimpleListFilter):
    title = 'Recent Activity'
    parameter_name = 'recent_activity'

    def lookups(self, request, model_admin):
        return (
            ('24h', 'Last 24 hours'),
            ('7d', 'Last 7 days'),
            ('30d', 'Last 30 days'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == '24h':
            return queryset.filter(created_at__gte=now - timedelta(hours=24))
        elif self.value() == '7d':
            return queryset.filter(created_at__gte=now - timedelta(days=7))
        elif self.value() == '30d':
            return queryset.filter(created_at__gte=now - timedelta(days=30))
        return queryset


class OTPStatusFilter(SimpleListFilter):
    title = 'OTP Status'
    parameter_name = 'otp_status'

    def lookups(self, request, model_admin):
        return OTP.OTP_STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class PaymentStatusFilter(SimpleListFilter):
    title = 'Payment Status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return Payment.PAYMENT_STATUS

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


# --- Inline Admin Classes ---
class OTPInline(admin.TabularInline):
    model = OTP
    extra = 0
    readonly_fields = ('id', 'hashed_code', 'status', 'expires_at', 'used_at', 'attempts', 'created_at')
    fields = ('otp_type', 'status', 'expires_at', 'attempts', 'max_attempts', 'used_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ('id', 'reference', 'paid_at', 'created_at', 'updated_at')
    fields = (
        ('id', 'reference'),
        ('amount', 'status'),
        ('paid_at',),
        ('ip_address', 'user_agent'),
        ('created_at', 'updated_at')
    )

    def has_delete_permission(self, request, obj=None):
        return False


# --- Custom User Admin ---
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        'email', 'full_name', 'phone_number', 'role',
        'account_status_badge', 'email_verified_badge',
        'failed_login_attempts', 'created_at'
    )
    list_filter = (
        AccountStatusFilter,
        EmailVerifiedFilter,
        'role',
        'is_staff',
        'is_superuser',
        RecentActivityFilter
    )
    search_fields = ('email', 'full_name', 'phone_number')
    ordering = ('-created_at',)
    readonly_fields = (
        'id', 'last_login', 'date_joined', 'created_at', 'updated_at',
        'email_verified_at', 'last_login_attempt', 'account_locked_until'
    )

    fieldsets = (
        ('Personal Info', {
            'fields': ('id', 'full_name', 'email', 'phone_number')
        }),
        ('Account Status', {
            'fields': (
                'role', 'account_status', 'is_active', 'is_staff', 'is_superuser',
                'email_verified', 'email_verified_at'
            )
        }),
        ('Security', {
            'fields': (
                'password', 'failed_login_attempts', 'account_locked_until',
                'last_login', 'last_login_attempt'
            )
        }),
        ('Timestamps', {
            'fields': ('date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': (
                'full_name', 'email', 'phone_number', 'role',
                'password', 'password2'
            ),
        }),
    )

    inlines = [OTPInline]
    actions = ['verify_email', 'activate_accounts', 'deactivate_accounts', 'unlock_accounts', 'export_users']

    def account_status_badge(self, obj):
        colors = {
            'pending_verification': 'orange',
            'active': 'green',
            'suspended': 'red',
            'deactivated': 'gray'
        }
        color = colors.get(obj.account_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_account_status_display()
        )
    account_status_badge.short_description = 'Status'

    def email_verified_badge(self, obj):
        if obj.email_verified:
            return format_html('<span style="color: green;">✓ Verified</span>')
        return format_html('<span style="color: red;">✗ Unverified</span>')
    email_verified_badge.short_description = 'Email'

    def verify_email(self, request, queryset):
        updated = 0
        for user in queryset:
            if not user.email_verified:
                user.verify_email()
                updated += 1
                log_custom_action(
                    action='admin_email_verified',
                    user=user,
                    details={'verified_by_admin': request.user.email},
                    request=request
                )
        self.message_user(request, f'Verified email for {updated} users.')
    verify_email.short_description = "Verify selected users' emails"

    def activate_accounts(self, request, queryset):
        updated = queryset.filter(account_status='pending_verification').update(
            account_status='active',
            email_verified=True,
            is_active=True
        )
        self.message_user(request, f'Activated {updated} accounts.')
    activate_accounts.short_description = "Activate selected accounts"

    def deactivate_accounts(self, request, queryset):
        updated = queryset.exclude(account_status='deactivated').update(
            account_status='deactivated',
            is_active=False
        )
        self.message_user(request, f'Deactivated {updated} accounts.')
    deactivate_accounts.short_description = "Deactivate selected accounts"

    def unlock_accounts(self, request, queryset):
        updated = 0
        for user in queryset.filter(account_locked_until__isnull=False):
            user.unlock_account()
            updated += 1
        self.message_user(request, f'Unlocked {updated} accounts.')
    unlock_accounts.short_description = "Unlock selected accounts"

    def export_users(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Email', 'Full Name', 'Phone', 'Role', 'Account Status',
            'Email Verified', 'Created At', 'Last Login'
        ])

        for user in queryset:
            writer.writerow([
                user.id, user.email, user.full_name, user.phone_number,
                user.role, user.account_status, user.email_verified,
                user.created_at, user.last_login
            ])

        log_custom_action(
            action='users_exported',
            details={'count': queryset.count()},
            request=request
        )

        return response
    export_users.short_description = "Export selected users to CSV"

    def get_queryset(self, request):
        return super().get_queryset(request)

    def save_model(self, request, obj, form, change):
        # Set the request context for the post_save signal
        set_request_context(
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            user=request.user
        )
        super().save_model(request, obj, form, change)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# --- OTP Admin ---
@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_email', 'otp_type', 'status_badge',
        'attempts', 'max_attempts', 'expires_at', 'created_at'
    )
    list_filter = (OTPStatusFilter, 'otp_type', RecentActivityFilter)
    search_fields = ('user__email', 'user__full_name', 'id')
    readonly_fields = (
        'id', 'hashed_code', 'used_at', 'created_at', 'updated_at',
        'ip_address', 'user_agent'
    )
    ordering = ('-created_at',)
    actions = ['invalidate_otps', 'cleanup_expired']

    fieldsets = (
        ('OTP Details', {
            'fields': ('id', 'user', 'otp_type', 'status')
        }),
        ('Security', {
            'fields': ('hashed_code', 'attempts', 'max_attempts', 'expires_at', 'used_at')
        }),
        ('Tracking', {
            'fields': ('ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'used': 'blue',
            'expired': 'orange',
            'invalidated': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def invalidate_otps(self, request, queryset):
        updated = queryset.filter(status='active').update(status='invalidated')
        self.message_user(request, f'Invalidated {updated} OTPs.')
    invalidate_otps.short_description = "Invalidate selected OTPs"

    def cleanup_expired(self, request, queryset):
        OTP.cleanup_expired_otps()
        self.message_user(request, 'Cleaned up expired OTPs.')
    cleanup_expired.short_description = "Cleanup expired OTPs"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# --- Telco Admin ---
@admin.register(Telco)
class TelcoAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active_badge', 'bundle_count', 'created_at')
    list_filter = ('is_active', RecentActivityFilter)
    search_fields = ('name', 'code')
    readonly_fields = ('id', 'created_at', 'updated_at')
    actions = ['activate_telcos', 'deactivate_telcos']

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'

    def bundle_count(self, obj):
        count = obj.bundle_set.filter(is_active=True).count()
        # Ensure the app name is correct in the reverse URL
        app_name = obj._meta.app_label
        url = reverse(f'admin:{app_name}_bundle_changelist') + f'?telco__id__exact={obj.id}'
        return format_html('<a href="{}">{} bundles</a>', url, count)
    bundle_count.short_description = 'Active Bundles'

    def activate_telcos(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} telcos.')
    activate_telcos.short_description = "Activate selected telcos"

    def deactivate_telcos(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} telcos.')
    deactivate_telcos.short_description = "Deactivate selected telcos"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            bundle_count=Count('bundle', filter=Q(bundle__is_active=True))
        )
    
    def save_model(self, request, obj, form, change):
        # Set the request context for the post_save signal
        set_request_context(
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            user=request.user
        )
        super().save_model(request, obj, form, change)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# --- Bundle Admin ---
@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = (
        'telco', 'name', 'is_instock', 'is_limited', 'size_mb', 'price', 'stock_status_badge',
        'is_active_badge', 'order_count', 'created_at'
    )
    list_filter = ('telco', 'name', 'is_instock', 'is_active', RecentActivityFilter)
    search_fields = ('telco__name', 'name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_editable = ('price', 'is_instock', 'is_limited')
    actions = ['mark_in_stock', 'mark_out_of_stock', 'activate_bundles', 'deactivate_bundles']

    fieldsets = (
        ('Bundle Details', {
            'fields': ('id', 'telco', 'name', 'size_mb', 'price')
        }),
        ('Stock Management', {
            'fields': ('is_instock', 'is_out_of_stock', 'is_limited', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def stock_status_badge(self, obj):
        if obj.is_out_of_stock:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.is_limited:
            return format_html('<span style="color: orange;">Limited</span>')
        elif obj.is_instock:
            return format_html('<span style="color: green;">In Stock</span>')
        return format_html('<span style="color: gray;">Unknown</span>')
    stock_status_badge.short_description = 'Stock Status'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    is_active_badge.short_description = 'Active'

    def order_count(self, obj):
        count = obj.databundleorder_set.count()
        # Ensure the app name is correct in the reverse URL
        app_name = obj._meta.app_label
        url = reverse(f'admin:{app_name}_databundleorder_changelist') + f'?bundle__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    order_count.short_description = 'Orders'

    def mark_in_stock(self, request, queryset):
        updated = queryset.update(is_instock=True, is_out_of_stock=False)
        self.message_user(request, f'Marked {updated} bundles as in stock.')
    mark_in_stock.short_description = "Mark as in stock"

    def mark_out_of_stock(self, request, queryset):
        updated = queryset.update(is_instock=False, is_out_of_stock=True)
        self.message_user(request, f'Marked {updated} bundles as out of stock.')
    mark_out_of_stock.short_description = "Mark as out of stock"

    def activate_bundles(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} bundles.')
    activate_bundles.short_description = "Activate selected bundles"

    def deactivate_bundles(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} bundles.')
    deactivate_bundles.short_description = "Deactivate selected bundles"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('telco').annotate(
            order_count=Count('databundleorder')
        )

    def save_model(self, request, obj, form, change):
        # Set the request context for the post_save signal
        set_request_context(
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            user=request.user
        )
        super().save_model(request, obj, form, change)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# --- Order Admin ---
@admin.register(DataBundleOrder)
class DataBundleOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_email', 'phone_number', 'bundle_info',
        'status_badge', 'payment_status', 'created_at'
    )
    list_filter = ('status', 'telco', 'created_at')
    search_fields = ('id', 'phone_number', 'user__email', 'provider_order_id')
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'ip_address', 'user_agent'
    )
    ordering = ('-created_at',)
    inlines = [PaymentInline]
    actions = ['mark_processing', 'mark_completed', 'mark_failed', 'export_orders']

    fieldsets = (
        ('Order Details', {
            'fields': ('id', 'user', 'telco', 'bundle', 'phone_number')
        }),
        ('Status', {
            'fields': ('status', 'provider_order_id')
        }),
        ('Tracking', {
            'fields': ('ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Customer'

    def bundle_info(self, obj):
        return f"{obj.bundle.name} - {obj.bundle.size_mb}MB"
    bundle_info.short_description = 'Bundle'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def payment_status(self, obj):
        try:
            payment = obj.payment
            colors = {
                'pending': 'orange',
                'success': 'green',
                'failed': 'red',
                'refunded': 'purple',
                'cancelled': 'gray'
            }
            color = colors.get(payment.status, 'gray')
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{}</span>',
                color,
                payment.get_status_display()
            )
        except Payment.DoesNotExist:
            return format_html('<span style="color: gray;">No Payment</span>')
    payment_status.short_description = 'Payment'

    def mark_processing(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='processing')
        self.message_user(request, f'Marked {updated} orders as processing.')
    mark_processing.short_description = "Mark as processing"

    def mark_completed(self, request, queryset):
        updated = queryset.filter(status__in=['pending', 'processing']).update(status='completed')
        self.message_user(request, f'Marked {updated} orders as completed.')
    mark_completed.short_description = "Mark as completed"

    def mark_failed(self, request, queryset):
        updated = queryset.exclude(status__in=['completed', 'failed']).update(status='failed')
        self.message_user(request, f'Marked {updated} orders as failed.')
    mark_failed.short_description = "Mark as failed"

    def export_orders(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Order ID', 'Customer Email', 'Phone Number', 'Telco', 'Bundle',
            'Bundle Size (MB)', 'Price', 'Status', 'Payment Status', 'Created At'
        ])

        for order in queryset.select_related('user', 'telco', 'bundle').prefetch_related('payment'):
            payment_status = 'No Payment'
            try:
                payment_status = order.payment.status
            except Payment.DoesNotExist:
                pass

            writer.writerow([
                order.id, order.user.email, order.phone_number,
                order.telco.name, order.bundle.name, order.bundle.size_mb,
                order.bundle.price, order.status, payment_status, order.created_at
            ])

        return response
    export_orders.short_description = "Export selected orders to CSV"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'telco', 'bundle'
        ).prefetch_related('payment')


# --- Payment Admin ---
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order_id', 'customer_email', 'amount',
        'status_badge', 'reference', 'paid_at', 'created_at'
    )
    list_filter = (PaymentStatusFilter, RecentActivityFilter)
    search_fields = ('id', 'reference', 'order__user__email', 'order__phone_number')
    readonly_fields = (
        'id', 'reference', 'paid_at', 'created_at', 'updated_at',
        'ip_address', 'user_agent'
    )
    ordering = ('-created_at',)
    actions = ['mark_success', 'mark_failed', 'export_payments']

    fieldsets = (
        ('Payment Details', {
            'fields': ('id', 'order', 'amount', 'reference', 'status')
        }),
        ('Timestamps', {
            'fields': ('paid_at', 'created_at', 'updated_at')
        }),
        ('Tracking', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        })
    )

    def order_id(self, obj):
        # Ensure the app name is correct in the reverse URL
        app_name = obj._meta.app_label
        url = reverse(f'admin:{app_name}_databundleorder_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.id)
    order_id.short_description = 'Order'

    def customer_email(self, obj):
        return obj.order.user.email
    customer_email.short_description = 'Customer'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'success': 'green',
            'failed': 'red',
            'refunded': 'purple',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def mark_success(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='success',
            paid_at=timezone.now()
        )
        self.message_user(request, f'Marked {updated} payments as successful.')
    mark_success.short_description = "Mark as successful"

    def mark_failed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='failed')
        self.message_user(request, f'Marked {updated} payments as failed.')
    mark_failed.short_description = "Mark as failed"

    def export_payments(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Payment ID', 'Order ID', 'Customer Email', 'Amount',
            'Reference', 'Status', 'Paid At', 'Created At'
        ])

        for payment in queryset.select_related('order__user'):
            writer.writerow([
                payment.id, payment.order.id, payment.order.user.email,
                payment.amount, payment.reference, payment.status,
                payment.paid_at, payment.created_at
            ])

        return response
    export_payments.short_description = "Export selected payments to CSV"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order__user')

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# --- Audit Log Admin ---
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_email', 'action', 'created_at', 'ip_address'
    )
    list_filter = ('action', RecentActivityFilter)
    search_fields = ('user__email', 'action', 'ip_address')
    readonly_fields = ('id', 'user', 'action', 'details', 'ip_address', 'user_agent', 'created_at')
    ordering = ('-created_at',)
    actions = ['export_audit_logs', 'cleanup_old_logs']

    fieldsets = (
        ('Audit Details', {
            'fields': ('id', 'user', 'action', 'created_at')
        }),
        ('Details', {
            'fields': ('details_formatted',)
        }),
        ('Tracking', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        })
    )

    def user_email(self, obj):
        return obj.user.email if obj.user else 'System'
    user_email.short_description = 'User'

    def details_formatted(self, obj):
        if obj.details:
            formatted_json = json.dumps(obj.details, indent=2, default=str)
            return format_html('<pre>{}</pre>', formatted_json)
        return 'No details'
    details_formatted.short_description = 'Details'

    def export_audit_logs(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User Email', 'Action', 'IP Address', 'Created At', 'Details'
        ])

        for log in queryset.select_related('user'):
            details = json.dumps(log.details, indent=2, default=str) if log.details else 'No details'
            writer.writerow([
                log.id, log.user.email if log.user else 'System', log.action,
                log.ip_address, log.created_at, details
            ])
        return response
    export_audit_logs.short_description = "Export selected audit logs to CSV"

    def cleanup_old_logs(self, request, queryset):
        cutoff_date = timezone.now() - timedelta(days=365)
        deleted_count, _ = AuditLog.objects.filter(created_at__lt=cutoff_date).delete()
        self.message_user(request, f'Cleaned up {deleted_count} old audit logs.')
    cleanup_old_logs.short_description = "Cleanup audit logs older than 1 year"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')