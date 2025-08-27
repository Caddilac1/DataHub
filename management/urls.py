from django.urls import path, include
from .views import AdminHomePageView, AdminDashboardView, AdminViewAllUsersView, AdminviewAllOrders, AdminViewAllBundle


urlpatterns = [
    path('admin_home_page/', AdminHomePageView.as_view(), name='admin_home_page'),
    path('admin_dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('view/users/', AdminViewAllUsersView.as_view(), name='view_all_users'),
    path('orders/all_orders/', AdminviewAllOrders.as_view(), name='view_all_orders'),
    path('bundles/view_all', AdminViewAllBundle.as_view(), name='admin_view_all_bundles'),
]