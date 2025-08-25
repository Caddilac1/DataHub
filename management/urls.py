from django.urls import path, include
from .views import AdminHomePageView, AdminDashboardView


urlpatterns = [
    path('admin_home_page/', AdminHomePageView.as_view(), name='admin_home_page'),
    path('admin_dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
]