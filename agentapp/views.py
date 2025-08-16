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

# Create your views here.


class AgentHomeView(TemplateView):
    template_name = 'home/home.html'

    def get(self, request, *args, **kwargs):
        bundles = Bundle.objects.select_related('telco').filter(is_agent_bundle=True).order_by('telco__name', 'size_mb')
        data_plans = {}

        for bundle in bundles:
            size_display = f"{bundle.size_mb // 1000}GB" if bundle.size_mb >= 1000 else f"{bundle.size_mb}MB"
            validity = "Non-Expiry" if bundle.telco.name.lower() in ['mtn', 'telecel'] else "30 days"

            provider_name = bundle.telco.name
            if provider_name not in data_plans:
                data_plans[provider_name] = []

            data_plans[provider_name].append({
                'id': bundle.id,
                'size': size_display,
                'price': f"GH₵ {bundle.price:.2f}",
                'validity': validity,
                'code': bundle.telco.code
            })

        context = {
            'data_plans': data_plans,
            'paystack_public_key': settings.TEST_PUBLIC_KEY,
            'user': request.user
        }

        return render(request, self.template_name, context)
