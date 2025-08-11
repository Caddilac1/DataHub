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
from .forms import EmailForm, OTPForm # Assuming you have these forms


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
                user.is_active = False # Deactivate until email is verified
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
                    'emails/otp_email.html', 
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
                
                # 5. Display success message and redirect
                messages.success(request, 'Registration successful! An OTP has been sent to your email. Please verify to log in.')
                return redirect(reverse('login'))

            except Exception as e:
                # Log the error for debugging
                print(f"Registration Error: {e}")
                messages.error(request, 'An unexpected error occurred during registration. Please try again later.')
                AuditLog.objects.create(
                    user=None, # User creation failed
                    action='user_created_failed', # Assuming you add this to your choices
                    details={'message': f'Registration failed due to an error: {str(e)}'},
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
        # If form is not valid, re-render the form with errors
        return render(request, 'authentication/registration/register.html', {'form': form})




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
        return render(request, 'authentication/registration/login.html', context)

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
                        auth.login(request, user)
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
                        return redirect('home')

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