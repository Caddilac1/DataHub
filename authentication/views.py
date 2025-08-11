from django.shortcuts import render
from django.views. generic import View

# Create your views here.

class RegisterView(View):
    template_name = 'authentication/register.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # Handle registration logic here
        pass