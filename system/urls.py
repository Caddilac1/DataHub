from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.conf.urls.static import static
from .views import *


urlpatterns = [
   path('', HomeView.as_view(), name='home'),
   path('tests/', TestHomeView.as_view(), name='test_home'),
   path('payment/', PaymentView.as_view(), name='payment_initiate'),
   path('payment/callback/', PaymentView.as_view(), name='payment_callback'),
   
]
