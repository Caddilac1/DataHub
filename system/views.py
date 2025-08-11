from django.shortcuts import render
from django.contrib.auth import login
import json
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages
from django.views.generic import TemplateView
from authentication.models import *
# Create your views here.


class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        bundles = Bundle.objects.select_related('telco').all().order_by('telco__name', 'size_mb')
        data_plans = {}

        for bundle in bundles:
            size_display = f"{bundle.size_mb // 1000}GB" if bundle.size_mb >= 1000 else f"{bundle.size_mb}MB"
            validity = "Non-Expiry" if bundle.telco.name.lower() in ['mtn', 'telecel'] else "30 days"

            provider_name = bundle.telco.name
            if provider_name not in data_plans:
                data_plans[provider_name] = []

            data_plans[provider_name].append({
                'size': size_display,
                'price': f"GH₵ {bundle.price:.2f}",
                'validity': validity,
                'code': bundle.telco.code
            })

        data_plans_json = json.dumps(data_plans)

        return self.render_to_response({
            'data_plans': data_plans,
            'data_plans_json': data_plans_json,
            'user': request.user  
        })



# Create your views here.




"""class HomeView(View):
    template_name = 'home/home.html'

    def get(self, request):
        context = {}
        return render(request, self.template_name, context)

"""