from django.urls import path, include
from .views import AdminHomePageView, AdminDashboardView, AdminViewAllUsersView


urlpatterns = [
    path('admin_home_page/', AdminHomePageView.as_view(), name='admin_home_page'),
    path('admin_dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('view/users/', AdminViewAllUsersView.as_view(), name='view_all_users'),
]