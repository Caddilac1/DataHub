from django.shortcuts import render
from django.views. generic import View
from packages.log_entry import create_log_entry
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import CustomUser
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from collections import defaultdict
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .models import *

# Create your views here.

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .forms import CustomUserCreationForm
from .models import CustomUser, OTP, AuditLog
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages, auth
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from .models import CustomUser, OTP, AuditLog
from .forms import EmailForm, OTPForm
from .models import verify_otp
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages, auth
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from .models import CustomUser, OTP, AuditLog # Assuming you have these models
from .forms import EmailForm, OTPForm, OTPVerificationForm # Assuming you have these forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import TruncMonth
from django.db.models import Count, Sum
from .models import DataBundleOrder, Payment
from django.views.generic import DetailView,ListView,CreateView,UpdateView,DeleteView
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta
from .models import CustomUser, DataBundleOrder, Bundle
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime, timedelta
from .models import CustomUser, DataBundleOrder, Bundle
import logging

logger = logging.getLogger(__name__)


class RegisterView(View):
    def get(self, request):
        form = CustomUserCreationForm()
        return render(request, 'authentication/registration/register.html', {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # 1. Create the user
                user = form.save(commit=False)
                user.account_status = "pending_verification" # Deactivate until email is verified
                user.save()

                # 2. Generate and save OTP
                otp_instance, otp_code = OTP.generate_otp(
                    user=user,
                    otp_type='email_verification',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # 3. Send OTP to user's email
                subject = 'DataHub - Confirm Your Email'
                html_message = render_to_string(
                    'authentication/emails/register_otp.html', 
                    {'user': user, 'otp_code': otp_code}
                )
                plain_message = strip_tags(html_message)
                from_email = settings.DEFAULT_FROM_EMAIL
                to_email = user.email
                
                send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)

                # 4. Create an audit log entry
                AuditLog.objects.create(
                    user=user,
                    action='user_created',
                    details={'message': 'User account created and verification OTP sent.'},
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # 5. Store email in session for the confirmation view
                request.session['registration_email'] = user.email
                
                # 6. Display success message and redirect to confirmation view
                messages.success(
                    request, 
                    'Registration successful! An OTP has been sent to your email. Please enter it below to verify your account.'
                )
                
                # Option 1: Redirect with email in URL (more reliable)
                return redirect(f"{reverse('confirm_email')}?email={user.email}")
                
                # Option 2: Simple redirect (relies on session only)
                # return redirect(reverse('confirm_email'))

            except Exception as e:
                # Log the error for debugging
                print(f"Registration Error: {e}")
                messages.error(request, 'An unexpected error occurred during registration. Please try again later.')
                AuditLog.objects.create(
                    user=None, # User creation failed
                    action='user_created_failed', # Make sure to add this to your AuditLog.ACTION_CHOICES
                    details={'message': f'Registration failed due to an error: {str(e)}'},
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
        # If form is not valid, re-render the form with errors
        return render(request, 'authentication/registration/register.html', {'form': form})


class CustomConfirmEmailView(View):
    """
    Handle email confirmation via OTP verification
    """
    template_name = 'authentication/registration/confirm_email.html'
    
    def get(self, request):
        """Display the OTP verification form"""
        # Get email from session or query params
        email = request.session.get('registration_email') or request.GET.get('email')
        
        if not email:
            messages.error(request, 'Invalid access. Please register again.')
            return redirect('register')
        
        # Check if user exists and needs verification
        user = CustomUser.get_by_email(email)
        if not user:
            messages.error(request, 'User not found. Please register again.')
            return redirect('register')
        
        if user.email_verified:
            messages.info(request, 'Your email is already verified. You can log in.')
            return redirect('login')
        
        form = OTPVerificationForm()
        context = {
            'form': form,
            'email': email,
            'user': user
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Process OTP verification"""
        email = request.session.get('registration_email') or request.POST.get('email')
        
        if not email:
            messages.error(request, 'Invalid access. Please register again.')
            return redirect('register')
        
        # Get the user
        user = CustomUser.get_by_email(email)
        if not user:
            messages.error(request, 'User not found. Please register again.')
            return redirect('register')
        
        if user.email_verified:
            messages.info(request, 'Your email is already verified. You can log in.')
            return redirect('login')
        
        form = OTPVerificationForm(request.POST)
        
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            
            try:
                # Get the most recent active OTP for email verification
                otp_instance = OTP.objects.filter(
                    user=user,
                    otp_type='email_verification',
                    status='active'
                ).order_by('-created_at').first()
                
                if not otp_instance:
                    messages.error(request, 'No valid OTP found. Please request a new verification email.')
                    return self._render_form_with_resend_option(request, form, email, user)
                
                # Verify the OTP
                if otp_instance.verify_code(otp_code):
                    # OTP is valid, verify the user's email
                    with transaction.atomic():
                        user.verify_email()  # This method updates email_verified, account_status, etc.
                        
                        # Create audit log
                        AuditLog.objects.create(
                            user=user,
                            action='email_verified',
                            details={
                                'message': 'Email successfully verified via OTP',
                                'otp_id': otp_instance.id
                            },
                            ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')
                        )
                    
                    # Clear the email from session
                    if 'registration_email' in request.session:
                        del request.session['registration_email']
                    
                    messages.success(
                        request, 
                        'Email verified successfully! Your account is now active. You can log in.'
                    )
                    return redirect('login')
                
                else:
                    # OTP verification failed
                    remaining_attempts = otp_instance.max_attempts - otp_instance.attempts
                    
                    if remaining_attempts > 0:
                        messages.error(
                            request, 
                            f'Invalid OTP. You have {remaining_attempts} attempt(s) remaining.'
                        )
                    else:
                        messages.error(
                            request, 
                            'Invalid OTP. Maximum attempts exceeded. Please request a new verification email.'
                        )
                        return self._render_form_with_resend_option(request, form, email, user)
                    
                    # Create audit log for failed verification
                    AuditLog.objects.create(
                        user=user,
                        action='otp_verification_failed',
                        details={
                            'message': 'Failed OTP verification attempt',
                            'otp_id': otp_instance.id,
                            'attempts_used': otp_instance.attempts
                        },
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
            
            except Exception as e:
                messages.error(request, 'An error occurred during verification. Please try again.')
                
                # Log the error
                AuditLog.objects.create(
                    user=user,
                    action='email_verification_error',
                    details={
                        'message': f'Email verification error: {str(e)}',
                        'error_type': type(e).__name__
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
        
        # If we get here, form validation failed or OTP verification failed
        context = {
            'form': form,
            'email': email,
            'user': user
        }
        return render(request, self.template_name, context)
    
    def _render_form_with_resend_option(self, request, form, email, user):
        """Helper method to render form with resend option"""
        context = {
            'form': form,
            'email': email,
            'user': user,
            'show_resend': True
        }
        return render(request, self.template_name, context)


class ResendVerificationOTPView(View):
    """
    Handle resending verification OTP
    """
    
    def post(self, request):
        """Resend OTP for email verification"""
        email = request.POST.get('email')
        
        if not email:
            messages.error(request, 'Email address is required.')
            return redirect('register')
        
        user = CustomUser.get_by_email(email)
        if not user:
            messages.error(request, 'User not found.')
            return redirect('register')
        
        if user.email_verified:
            messages.info(request, 'Your email is already verified.')
            return redirect('login')
        
        try:
            # Generate new OTP
            otp_instance, otp_code = OTP.generate_otp(
                user=user,
                otp_type='email_verification',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Send email (you'll need to import the necessary modules)
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            from django.conf import settings
            
            subject = 'DataHub - Confirm Your Email (Resent)'
            html_message = render_to_string(
                'authentication/emails/register_otp.html',
                {'user': user, 'otp_code': otp_code}
            )
            plain_message = strip_tags(html_message)
            from_email = settings.DEFAULT_FROM_EMAIL
            
            send_mail(
                subject, 
                plain_message, 
                from_email, 
                [user.email], 
                html_message=html_message
            )
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action='otp_resent',
                details={
                    'message': 'Verification OTP resent to user email',
                    'otp_id': otp_instance.id
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, 'A new verification code has been sent to your email.')
            
        except Exception as e:
            messages.error(request, 'Failed to resend verification code. Please try again later.')
            
            # Log the error
            AuditLog.objects.create(
                user=user,
                action='otp_resend_failed',
                details={
                    'message': f'Failed to resend OTP: {str(e)}',
                    'error_type': type(e).__name__
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        return redirect(f"{reverse('confirm_email')}?email={email}")


class CustomLogoutView(View):
    def get(self, request):
        if request.user.is_authenticated:   
             user = request.user
             AuditLog.objects.create(
                user=user,
                action='user_logout',
                details={
                    'message': f"User {user.full_name} has logged out successfully.",
                    'session_key': request.session.session_key
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
             create_log_entry(
                user=request.user,
                content_type=ContentType.objects.get_for_model(CustomUser),
                object_id=request.user.pk,
                object_repr=str(request.user),
                action_flag=2,  # CHANGE action
                change_message=f"User {request.user.full_name} has logged out successfully"
            )
             logout(request)
             messages.success(request, "You have been successfully logged out. See you soon!")
            

             return redirect('login')
        else:
            return redirect('home')
        



class CustomLoginView(View):
    def get(self, request):
        email_form = EmailForm()
        otp_form = OTPForm()
        
        # Determine which form to show based on session state
        show_otp_form = 'otp_sent_to_email' in request.session
        
        context = {
            'email_form': email_form,
            'otp_form': otp_form,
            'show_otp_form': show_otp_form
        }
        return render(request, 'authentication/registration/login2.html', context)

    def post(self, request):
        # Handle email submission (initial or resend)
        if 'request_otp' in request.POST:
            # Use the email from the POST data if it's the first submission,
            # otherwise get it from the session for a resend request.
            email = request.POST.get('email')
            
            # If the email isn't in POST data, it might be a resend request
            # from the OTP form. Get it from the session.
            if not email:
                email = request.session.get('otp_sent_to_email')

            email_form = EmailForm({'email': email})

            if email_form.is_valid():
                email = email_form.cleaned_data['email']
                try:
                    user = CustomUser.objects.get(email=email)
                    
                    if not user.is_active:
                        messages.error(request, 'This account is not active. Please check your email for the activation link.')
                        return redirect(reverse('login'))

                    # Generate and save a new OTP
                    otp_instance, otp_code = OTP.generate_otp(
                        user=user,
                        otp_type='login_verification',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                    
                    # Send OTP to user's email
                    subject = 'DataHub - Your Login OTP'
                    html_message = render_to_string(
                        'authentication/emails/otp_login_email.html',
                        {'user': user, 'otp_code': otp_code}
                    )
                    plain_message = strip_tags(html_message)
                    send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)

                    # Store email in session to verify OTP later
                    request.session['otp_sent_to_email'] = email
                    
                    messages.success(request, 'A new OTP has been sent to your email. Please enter it below to log in.')
                    return redirect(reverse('login'))

                except CustomUser.DoesNotExist:
                    messages.error(request, 'No account found with this email.')
                    AuditLog.objects.create(
                        user=None,
                        action='login_failed_email',
                        details={'message': f"Attempted login with non-existent email: {email}"},
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
            
            # If the email form is invalid (e.g., empty email), it's the initial submission.
            # Rerender the page with the error messages.
            messages.error(request, 'Invalid email address or account not found.')
            return redirect(reverse('login'))

        # Handle OTP Verification
        elif 'verify_otp' in request.POST:
            otp_form = OTPForm(request.POST)
            email = request.session.get('otp_sent_to_email')
            
            if otp_form.is_valid() and email:
                otp_code = otp_form.cleaned_data['otp']
                try:
                    user = CustomUser.objects.get(email=email)
                    
                    # Find the most recent active OTP for this user and type
                    latest_otp = OTP.objects.filter(
                        user=user, 
                        otp_type='login_verification',
                        status='active'
                    ).order_by('-created_at').first()

                    # Check if OTP is valid and not expired
                    if latest_otp and latest_otp.verify_code(otp_code):
                        auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                        AuditLog.objects.create(
                            user=user,
                            action='login_successful',
                            details={'message': "User logged in with OTP."},
                            ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')
                        )
                        # Clear session data after successful login
                        del request.session['otp_sent_to_email']
                        messages.success(request, f"Welcome back, {user.full_name}!")
                        if user.role == 'agent':
                            return redirect('agent_home_page')
                        elif user.role == 'customer':
                            return redirect('home')
                        elif user.role == 'admin':
                            return redirect('admin:index')

                    else:
                        messages.error(request, 'Invalid or expired OTP. Please try again.')
                        AuditLog.objects.create(
                            user=user,
                            action='login_failed_otp',
                            details={'message': "Invalid or expired OTP entered."},
                            ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')
                        )

                except CustomUser.DoesNotExist:
                    messages.error(request, 'An unexpected error occurred. Please try again.')
                    
            else:
                messages.error(request, 'Invalid OTP. Please try again.')

        # If any form is invalid or an error occurs, re-render the page with forms
        return redirect(reverse('login'))
    


class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user

        # Fetch user's orders and payments
        user_orders = DataBundleOrder.objects.filter(user=user).order_by('-created_at')
        user_payments = Payment.objects.filter(order__user=user).order_by('-created_at')

        # 2. Perform monthly order analysis
        monthly_orders = user_orders.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id'),
            total_price=Sum('bundle__price')
        ).order_by('month')

        # 3. Determine user's role and account status
        user_role = user.get_role_display()
        account_status = user.get_account_status_display()

        context = {
            'user': user,
            'account_status': account_status,
            'user_role': user_role,
            'user_orders': user_orders,
            'monthly_orders': monthly_orders,
            'user_payments': user_payments,
        }

        return render(request, 'authentication/profiles/user_profile.html', context)




class CustomerOrderHistory(LoginRequiredMixin, ListView):
    model = DataBundleOrder
    template_name = 'authentication/profiles/customer_order_history.html'
    context_object_name = 'orders'
    paginate_by = 20  # Add pagination for better performance
    
    def get_queryset(self):
        """Get orders for the current user with optimized queries"""
        try:
            # Use select_related to avoid N+1 queries
            queryset = DataBundleOrder.objects.filter(
                user=self.request.user
            ).select_related(
                'bundle', 
                'bundle__telco', 
                'telco'
            ).order_by('-created_at')
            
            return queryset
            
        except Exception as e:
            logger.error(f"Error fetching orders for user {self.request.user.id}: {str(e)}")
            return DataBundleOrder.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            customer = self.request.user
            orders = self.get_queryset()
            
            # Basic order counts with safe defaults
            context.update({
                'customer': customer,
                'orders': orders,
                'total_orders_count': orders.count() if orders.exists() else 0,
            })
            
            # Only calculate additional statistics if orders exist
            if orders.exists():
                context.update(self._get_order_statistics(orders))
                context.update(self._get_monthly_analysis(orders))
                context.update(self._get_additional_analytics(orders))
            else:
                # Provide safe defaults when no orders exist
                context.update({
                    'completed_orders_count': 0,
                    'pending_orders_count': 0,
                    'failed_orders_count': 0,
                    'processing_orders_count': 0,
                    'cancelled_orders_count': 0,
                    'monthly_orders': [],
                    'most_used_telco': None,
                    'total_spent': 0,
                    'average_order_value': 0,
                })
        
        except Exception as e:
            logger.error(f"Error in CustomerOrderHistory context: {str(e)}")
            # Provide safe fallbacks in case of any error
            context.update({
                'orders': DataBundleOrder.objects.none(),
                'total_orders_count': 0,
                'completed_orders_count': 0,
                'pending_orders_count': 0,
                'failed_orders_count': 0,
                'processing_orders_count': 0,
                'cancelled_orders_count': 0,
                'monthly_orders': [],
                'most_used_telco': None,
                'total_spent': 0,
                'average_order_value': 0,
            })
    
        return context
    
    def _get_order_statistics(self, orders):
        """Calculate order statistics by status"""
        try:
            stats = orders.aggregate(
                completed_count=Count('id', filter=Q(status='completed')),
                pending_count=Count('id', filter=Q(status='pending')),
                failed_count=Count('id', filter=Q(status='failed')),
                processing_count=Count('id', filter=Q(status='processing')),
                cancelled_count=Count('id', filter=Q(status='cancelled')),
            )
            
            return {
                'completed_orders_count': stats.get('completed_count', 0),
                'pending_orders_count': stats.get('pending_count', 0),
                'failed_orders_count': stats.get('failed_count', 0),
                'processing_orders_count': stats.get('processing_count', 0),
                'cancelled_orders_count': stats.get('cancelled_count', 0),
            }
            
        except Exception as e:
            logger.error(f"Error calculating order statistics: {str(e)}")
            return {
                'completed_orders_count': 0,
                'pending_orders_count': 0,
                'failed_orders_count': 0,
                'processing_orders_count': 0,
                'cancelled_orders_count': 0,
            }
    
    def _get_monthly_analysis(self, orders):
        """Calculate monthly order analysis"""
        try:
            monthly_data = orders.annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id'),
                total_price=Sum('bundle__price'),
                average_price=Avg('bundle__price')
            ).order_by('-month')
            
            # Convert to list and handle None values
            monthly_orders = []
            for item in monthly_data:
                monthly_orders.append({
                    'month': item['month'],
                    'count': item.get('count', 0),
                    'total_price': item.get('total_price', 0) or 0,
                    'average_price': item.get('average_price', 0) or 0,
                })
            
            return {'monthly_orders': monthly_orders}
            
        except Exception as e:
            logger.error(f"Error calculating monthly analysis: {str(e)}")
            return {'monthly_orders': []}
    
    def _get_additional_analytics(self, orders):
        """Calculate additional analytics like most used telco, total spent, etc."""
        try:
            # Most used telco
            most_used_telco = orders.values('bundle__telco__name').annotate(
                count=Count('id')
            ).order_by('-count').first()
            
            # Financial statistics
            financial_stats = orders.aggregate(
                total_spent=Sum('bundle__price'),
                average_order_value=Avg('bundle__price')
            )
            
            total_spent = financial_stats.get('total_spent') or 0
            average_order_value = financial_stats.get('average_order_value') or 0

            return {
                'most_used_telco': most_used_telco['bundle__telco__name'] if most_used_telco else None,
                'total_spent': total_spent,
                'average_order_value': average_order_value,
            }

        except Exception as e:
            logger.error(f"Error calculating additional analytics: {str(e)}")
            return {
                'most_used_telco': None,
                'total_spent': 0,
                'average_order_value': 0,
            }