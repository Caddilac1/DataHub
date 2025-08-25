from django.shortcuts import render
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, View
from packages.decorators import admin_required
from django.utils.decorators import method_decorator  
from django.db.models import Count, Sum, F  

# Create your views here.


from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from authentication.models import (
    AuditLog,
    CustomUser,
    DataBundleOrder,
    SystemConfiguration,
    OTP,
    Payment
)
from authentication.models import *
from django.db.models.functions import TruncMonth


# Ensure this path is correct based on your project structure
@method_decorator(admin_required, name='dispatch')
class AdminHomePageView(LoginRequiredMixin,TemplateView):
    template_name = 'management/admin_home_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Admin Dashboard'
        context['page_header'] = 'Dashboard'
        
        # Fetching key data for the dashboard
        context.update(self.get_dashboard_metrics())
        
        # Fetching recent system logs
        context['recent_audit_logs'] = AuditLog.objects.select_related('user').order_by('-created_at')[:10]
        
        # Fetching system configurations
        context['system_configs'] = SystemConfiguration.objects.all()

        return context

    def get_dashboard_metrics(self):
        # Count of users by role
        user_role_counts = CustomUser.objects.values('role').annotate(count=Count('role'))
        user_counts = {item['role']: item['count'] for item in user_role_counts}
        
        # Count of orders by status
        order_status_counts = DataBundleOrder.objects.values('status').annotate(count=Count('status'))
        order_counts = {item['status']: item['count'] for item in order_status_counts}
        
        # Count of OTPs by status
        otp_status_counts = OTP.objects.values('status').annotate(count=Count('status'))
        otp_counts = {item['status']: item['count'] for item in otp_status_counts}

        # Calculate pending verification users
        pending_verification_users = CustomUser.objects.filter(email_verified=False, account_status='pending_verification').count()
        
        return {
            'total_users': CustomUser.objects.count(),
            'user_counts_by_role': user_counts,
            'pending_verification_users': pending_verification_users,
            'total_orders': DataBundleOrder.objects.count(),
            'order_counts_by_status': order_counts,
            'total_otps': OTP.objects.count(),
            'otp_counts_by_status': otp_counts,
        }





@method_decorator(admin_required, name='dispatch')
class AdminDashboardView(LoginRequiredMixin,TemplateView):
    template_name = 'management/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Admin Dashboard'
        context['page_header'] = 'Dashboard'

        # Fetch key metrics and analysis
        context.update(self.get_dashboard_metrics())

        # Fetch monthly activity analysis
        context.update(self.get_monthly_analysis())

        # Perform system health checks
        context.update(self.perform_system_health_checks())
        
        # Fetch recent system logs
        context['recent_audit_logs'] = AuditLog.objects.select_related('user').order_by('-created_at')[:10]
        
        # Fetch system configurations
        context['system_configs'] = SystemConfiguration.objects.all()

        return context

    def get_dashboard_metrics(self):
        return {
            'total_users': CustomUser.objects.count(),
            'total_orders': DataBundleOrder.objects.count(),
            'total_revenue': Payment.objects.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0,
            'orders_by_status': DataBundleOrder.objects.values('status').annotate(count=Count('status')),
        }

    def get_monthly_analysis(self):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=180) # Last 6 months

        # Monthly order trends
        monthly_orders = DataBundleOrder.objects.filter(
            created_at__gte=start_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        # Monthly user sign-up trends
        monthly_signups = CustomUser.objects.filter(
            created_at__gte=start_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        # Format data for charts
        order_months = [item['month'].strftime('%b %Y') for item in monthly_orders]
        order_counts = [item['count'] for item in monthly_orders]
        signup_months = [item['month'].strftime('%b %Y') for item in monthly_signups]
        signup_counts = [item['count'] for item in monthly_signups]

        return {
            'order_months': order_months,
            'order_counts': order_counts,
            'signup_months': signup_months,
            'signup_counts': signup_counts,
        }

    def perform_system_health_checks(self):
        health_issues = []

        # Check for orders without a corresponding payment
        orders_without_payment = DataBundleOrder.objects.filter(
            status__in=['pending', 'processing'],
            payment__isnull=True
        ).count()
        if orders_without_payment > 0:
            health_issues.append(f"⚠️ {orders_without_payment} pending/processing orders have no associated payment record.")

        # Check for completed orders with failed payments
        completed_orders_with_failed_payments = DataBundleOrder.objects.filter(
            status='completed',
            payment__status='failed'
        ).count()
        if completed_orders_with_failed_payments > 0:
            health_issues.append(f"🚨 {completed_orders_with_failed_payments} completed orders have failed payment statuses. This indicates a data inconsistency.")

        # Check for payments with no order
        payments_without_order = Payment.objects.filter(order__isnull=True).count()
        if payments_without_order > 0:
            health_issues.append(f"🚨 {payments_without_order} payments exist without a corresponding order.")

        # Check for users with active status but unverified emails
        users_inconsistency = CustomUser.objects.filter(
            account_status='active', 
            email_verified=False
        ).count()
        if users_inconsistency > 0:
            health_issues.append(f"🚨 {users_inconsistency} users are marked 'active' but their email is not verified.")

        # Check for missing Telco or Bundle records
        orders_with_missing_telco = DataBundleOrder.objects.filter(telco__isnull=True).count()
        if orders_with_missing_telco > 0:
            health_issues.append(f"🚨 {orders_with_missing_telco} orders have no associated Telco record.")

        return {'health_issues': health_issues}
    

@method_decorator(admin_required, name='dispatch')
class AdminViewAllUsersView(LoginRequiredMixin,TemplateView):
    template_name = 'management/admin_view_all_users.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'All Users'
        context['page_header'] = 'User Management'
        context['users'] = CustomUser.objects.all().order_by('-created_at')
        return context