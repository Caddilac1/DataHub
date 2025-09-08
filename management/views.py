from django.shortcuts import render
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, View, ListView, DetailView  
from packages.decorators import admin_required, closing_time
from django.utils.decorators import method_decorator  
from django.db.models import Count, Sum, F  
from django.db.models import Q
from packages.log_entry import create_log_entry
import traceback
from django.contrib.contenttypes.models import ContentType
from itertools import chain
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.shortcuts import render, redirect
from django.views import View

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
    Payment,
    Bundle
)
from authentication.models import *
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import *
from django.urls import reverse


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
    

@method_decorator(admin_required, name='dispatch')
class AdminviewAllOrders(LoginRequiredMixin, ListView):
    model = DataBundleOrder
    template_name = 'management/admin_view_all_orders.html'
    context_object_name = 'orders'
    paginate_by = 20  # Show 20 orders per page

    def get_queryset(self):
        return DataBundleOrder.objects.select_related('user', 'telco', 'bundle', 'payment').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders = DataBundleOrder.objects.select_related('user', 'telco', 'bundle', 'payment').order_by('-created_at')
        total_pending_orders = orders.filter(status='pending').count()
        total_processing_orders = orders.filter(status='processing').count()
        total_failed_orders = orders.filter(status='failed').count()
        total_cancelled_orders = orders.filter(status='cancelled').count()
        total_completed_orders = orders.filter(status='completed').count()
        
        context['title'] = 'All Orders'
        context['total_pending_orders'] = total_pending_orders
        context['total_processing_orders'] = total_processing_orders
        context['total_failed_orders'] = total_failed_orders
        context['total_cancelled_orders'] = total_cancelled_orders 
        context['total_completed_orders'] = total_completed_orders 
        context['page_header'] = 'Order Management'
        return context




class AdminViewAllBundle(LoginRequiredMixin,ListView):
    model = Bundle
    context_object_name = 'bundles'
    template_name = 'management/bundles/admin_view_all_bundles.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_name'] = 'data_bundles'
        context['list_name'] = 'bundle_lists'
        context['total_bundles'] = self.get_queryset().count()
        context['total_active_bundles'] = self.get_queryset().filter(is_active=True).count()
        context['total_inactive_customer_bundles'] = self.get_queryset().filter(is_active=False, is_agent_bundle=False).count()
        context['total_active_customer_bundles'] = self.get_queryset().filter(is_active=True, is_agent_bundle=False).count()
        context['total_agent_active_bundles'] = self.get_queryset().filter(is_active=True, is_agent_bundle=True).count()
        context['total_inactive_bundles'] = self.get_queryset().filter(is_active=False).count()
        context['total_inactive_agent_bundles'] = self.get_queryset().filter(is_active=False, is_agent_bundle=True).count()
        return context
    

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(telco__icontains=search_query) |
                Q(price__icontains=search_query) |
                Q(is_agent_bundle__icontains=search_query) |
                Q(is_in_stock__icontains=search_query) |
                Q(is_limited__icontains=search_query) |
                Q(is_active__icontains=search_query) |
                Q(size_mb__icontains=search_query)
            )


        return queryset
    


class AdminViewBundleDetailsView(LoginRequiredMixin, DetailView):
    model = Bundle
    template_name = 'management/agent_view_bundle_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_name'] = 'bundle_details_page'
        context['list_name'] = 'bundle_lists'
        return context
    
    def get_object(self):
        return get_object_or_404(Bundle, id= self.kwargs['id'])
    



@method_decorator([login_required, closing_time, admin_required], name='dispatch')
class AdminRegisterStaffView(CreateView):
    model = CustomUser
    template_name = 'management/authentication/staff/create_staff.html'
    form_class = RegisterStaffForm

    def form_valid(self, form):
        user = form.save(commit=False)
        user.username = f"user_{form.cleaned_data['username']}"
        
        user.save()
        subject = 'DataHub - Your Login OTP'
        html_message = render_to_string(
                        'authentication/emails/otp_login_email.html',
                        {'user': user,}
                    )
        message = f"Dear {user.get_full_name()}, \nYou have been enrolled as a Staff at Datahub . Your Staff ID is {user.pk}."
        send_mail(user.email, message) 

        # Log the user creation
        create_log_entry(
            user=self.request.user,
            content_type=ContentType.objects.get_for_model(CustomUser),
            object_id=self.request.user.pk,
            object_repr=str(self.request.user),
            action_flag=1,
            change_message=f"Admin {self.request.user.full_name} created a new staff: {user.full_name}"
        )
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('admin_staff_detail', kwargs={'user_id': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_name'] = 'create_staff'
        context['list_name'] = 'staffs'
        return context



@method_decorator([login_required, closing_time, admin_required], name='dispatch')
class AdminStaffDetailView(DetailView):
    model = CustomUser
    template_name = 'management/authentication/staff/staff_detail.html'
    context_object_name = 'staff'
    slug_field = 'user_id'
    slug_url_kwarg = 'user_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        deposits = Deposit.objects.filter(staff=self.get_object()).order_by('created_at')
        withdrawals = Withdrawal.objects.filter(staff=self.get_object()).order_by('created_at')
        

        # Combine all the transaction and Sort the transactions by timestamp
        transactions = sorted(
            chain(deposits, withdrawals),
            key=lambda x: x.created_at,
            reverse=True
        )
        
        all_transactions = transactions
        recent_transactions = transactions[:5]
        
        context['page_name'] = 'staff_detail'
        context['list_name'] = 'staffs'
        context['all_transactions'] = all_transactions
        context['recent_transactions'] = recent_transactions
        
        
        return context 
    