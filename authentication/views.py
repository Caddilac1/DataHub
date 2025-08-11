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

class RegisterView(View):
    template_name = 'authentication/register.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # Handle registration logic here
        pass




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