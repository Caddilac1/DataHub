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

# Create your views here.
def HomeView(request):
    return render(request, 'home.html')



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
