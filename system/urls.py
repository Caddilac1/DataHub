from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.conf.urls.static import static
from .views import *

urlpatterns = [
   path('', HomeView.as_view(), name='home'),
   path('register/', CustomerRegisterView.as_view(), name='register'),
   path('login/', UserLoginView.as_view(), name='login'),
   path('logout/', UserLogoutView.as_view(), name='logout'),
]
