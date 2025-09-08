from django import forms  
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth.forms import AuthenticationForm
from django.forms import ModelForm
from django import forms
from authentication.models import *



class RegisterStaffForm(UserCreationForm): 
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password', 'autocomplete':'off'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password', 'autocomplete':'off'})
    )
   
    
    # Checking for already existing mails...
    def clean_email(self):
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exclude(username=username).count():
            raise forms.ValidationError('This email is already in use! Try another email.')
        return email
    
    #checking for existing phone numbers
    def clean_phone(self):
        username = self.cleaned_data.get('username')
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and CustomUser.objects.filter(phone_number=phone_number).exclude(username=username).count():
            raise forms.ValidationError('This Phone Number is already in use! Try another phone number.')
        return phone_number
    
    
    class Meta:
        model = CustomUser
        fields = ['full_name', 'email','phone_number',  'role',]
        
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class':'custom-select2 form-control',}),

            
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set initial values for checkboxes based on the instance data
        if self.instance:
            self.fields['role'].initial = "customer"