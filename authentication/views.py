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
        return render(request, 'registration/register.html', {'form': form})




class LogoutView(View):
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