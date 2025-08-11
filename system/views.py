from django.shortcuts import render
from django.contrib.auth import login
from django.views.generic.edit import FormView
from .forms import CustomerRegistrationForm
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import EmailLoginForm
from .models import CustomUser
from django.contrib import messages
from django.contrib.auth.views import LogoutView
from django.views.generic import View, CreateView,UpdateView, DetailView, DeleteView, ListView

# Create your views here.
def HomeView(request):
    return render(request, 'home.html')



class HomeView(View):
    template_name = 'home/home.html'

    def get(self, request):
        context = {}
        return render(request, self.template_name, context)

