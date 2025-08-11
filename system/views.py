from django.shortcuts import render
from django.contrib.auth import login
import json
from django.views.generic.edit import FormView
from .forms import CustomerRegistrationForm
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import EmailLoginForm
from .models import *
from django.views import View
from django.contrib import messages
from django.contrib.auth.views import LogoutView
from django.views.generic import TemplateView
from .models import Bundle
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

class CustomerRegisterView(FormView):
    template_name = "register.html"
    form_class = CustomerRegistrationForm
    success_url = reverse_lazy("home")  

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)





class UserLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.role == 'admin':
            return reverse_lazy('home')
        elif user.role == 'agent':
            return reverse_lazy('home')
        return reverse_lazy('home')


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('login') 
