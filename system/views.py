from django.shortcuts import render
from django.contrib.auth import login
import json
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages
from django.db.models import Count, Q
from django.views.generic import ListView
from django.views.generic import TemplateView
from authentication.models import *
# Create your views here.


class HomeView(TemplateView):
    template_name = 'home/home.html'

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


class TelcoStockListView(ListView):
    model = Telco
    template_name = "telcos.html"
    context_object_name = "telcos"

    def get_queryset(self):
        # Annotate each Telco with counts of in-stock and out-of-stock bundles
        return Telco.objects.annotate(
            total_bundles=Count('bundle'),
            in_stock_bundles=Count('bundle', filter=Q(bundle__is_instock=True)),
            out_stock_bundles=Count('bundle', filter=Q(bundle__is_instock=False)),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for telco in context["telcos"]:
            if telco.in_stock_bundles == telco.total_bundles and telco.total_bundles > 0:
                telco.stock_status = "in-stock"
            elif telco.in_stock_bundles > 0:
                telco.stock_status = "limited"
            else:
                telco.stock_status = "out-of-stock"
        return context
