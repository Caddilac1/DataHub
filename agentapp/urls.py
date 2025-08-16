from django.urls import path
from .views import *
from . import views


urlpatterns = [
    path('agent_home_page/', AgentHomeView.as_view(), name='agent_home_page'),
]