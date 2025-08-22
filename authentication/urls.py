from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.conf.urls.static import static
from .views import *
from system.views import *

urlpatterns = [
   path('register/', RegisterView.as_view(), name='register'),
   path('signout/', CustomLogoutView.as_view(), name='signout'),
   path('login/', CustomLoginView.as_view(), name='login'),
   path('confirm-email/', CustomConfirmEmailView.as_view(), name='confirm_email'),
   path('resend-otp/', ResendVerificationOTPView.as_view(), name='resend_otp'),
   
]