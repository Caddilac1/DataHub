from django.shortcuts import render
from django.views.generic import CreateView, UpdateView, ListView, DeleteView, DetailView, View, TemplateView
from django.conf import settings
from authentication.models import Bundle,DataBundleOrder
from django.contrib.auth import login
import json
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages
from django.db.models import Count, Q
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from authentication.models import *
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from authentication.models import Bundle, DataBundleOrder, Payment
from system.services import initialize_paystack_payment, verify_paystack_payment
import logging
from django.conf import settings
logger = logging.getLogger(__name__)
from django.utils.decorators import method_decorator
from packages.decorators import agent_required
from django.utils import timezone
from packages.decorators import closing_time
from packages.decorators import admin_required
from django.contrib.auth.decorators import login_required

# Create your views here.

@method_decorator(agent_required, name='dispatch')
class AgentHomeView(LoginRequiredMixin, TemplateView):
    """
    A class-based view to display the home page with bundles categorized by telco,
    without using JSON for client-side rendering.
    """
    template_name = 'agents/home/home.html'

    def get_context_data(self, **kwargs):
        """
        Populate the context with a structured dictionary of data plans.
        """
        context = super().get_context_data(**kwargs)
        
        bundles = Bundle.objects.select_related('telco').filter(is_agent_bundle=True).order_by('telco__name', 'size_mb')
        data_plans = {}

        orders = DataBundleOrder.objects.filter(user=self.request.user).order_by('-created_at')
        paginator = Paginator(orders, 15)  # 15 per page
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        today = timezone.now().date()
        rec_orders = DataBundleOrder.objects.filter(created_at__date=today).order_by('-created_at')

        for bundle in bundles:
            size_display = f"{bundle.size_mb // 1000}GB" if bundle.size_mb >= 1000 else f"{bundle.size_mb}MB"
            validity = "Non-Expiry" if bundle.telco.name.lower() in ['mtn', 'telecel'] else "30 days"

            provider_name = bundle.telco.name
            if provider_name not in data_plans:
                data_plans[provider_name] = []

            data_plans[provider_name].append({
                'id': bundle.id,
                'size': size_display,
                'price': f"{bundle.price:.2f}",  # Keep price as string for display
                'validity': validity,
                'code': bundle.telco.code
            })
        
        context['data_plans'] = data_plans
        context['paystack_public_key'] = settings.TEST_PUBLIC_KEY  # Use the test public key for client-side integration
        context['user'] = self.request.user 
        context['orders'] = orders  # Include user's past orders for display
        context['rec_orders'] = rec_orders  # Include recent orders for display
        context['page_obj'] = page_obj  # Pass the paginated orders to the template 
 # Pass the user object to the template for
        
        return context
    
