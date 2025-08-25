# authentication/forms.py

from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from allauth.account.forms import SignupForm

from .models import CustomUser
from .models import *

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('full_name', 'email', 'phone_number')

    def clean_email(self):
        # Ensure email is not already in use
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def clean_phone_number(self):
        # Ensure phone number is not already in use
        phone_number = self.cleaned_data.get('phone_number')
        if CustomUser.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("A user with that phone number already exists.")
        
        # Basic format validation (optional, can be done in the model too)
        if not phone_number.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValidationError("Invalid phone number format.")
            
        return phone_number

    def save(self, commit=True):
        # Call the superclass's save method to create the user
        user = super().save(commit=False)
        
        # Additional fields are saved automatically by the form,
        # but we can set defaults here if needed before the final save.
        user.is_active = False # Deactivate user until email is verified
        
        if commit:
            user.save()
        return user
    

# authentication/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import CustomUser

class EmailForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        max_length=254,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email address', 'class': 'form-input','id': 'id_password'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not CustomUser.objects.filter(email=email).exists():
            raise ValidationError("No account found with this email address.")
        return email

class OTPForm(forms.Form):
    otp = forms.CharField(
        label="OTP",
        max_length=6,
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit OTP', 'class': 'form-input', 'id': 'id_password'}),
    )

class SocialSignupForm(SignupForm):
    class Meta:
        model = CustomUser
        fields = ["phone_number"]

    def __init__(self, *args, **kwargs):
        self.sociallogin = kwargs.pop("sociallogin", None)  # safer
        super().__init__(*args, **kwargs)
        self.fields["phone_number"].required = True

    def save(self, request):
        user = super().save(request)

        if self.sociallogin:
            extra_data = self.sociallogin.account.extra_data
            given_name = extra_data.get("given_name", "")
            family_name = extra_data.get("family_name", "")

            # If your model has full_name
            if hasattr(user, "full_name") and not user.full_name:
                user.full_name = f"{given_name} {family_name}".strip()
            else:
                # fallback if only first_name/last_name exist
                if not user.first_name:
                    user.first_name = given_name
                if not user.last_name:
                    user.last_name = family_name

        user.phone_number = self.cleaned_data.get("phone_number")
        user.save()
        return user



class OTPVerificationForm(forms.Form):
    """Form for OTP verification"""
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': 'Enter 6-digit code',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric'
        }),
        help_text='Enter the 6-digit code sent to your email'
    )
    
    email = forms.EmailField(
        widget=forms.HiddenInput()  # Hidden field to maintain email context
    )
    
    def clean_otp_code(self):
        otp_code = self.cleaned_data.get('otp_code')
        
        if not otp_code.isdigit():
            raise forms.ValidationError('OTP must contain only numbers.')
        
        if len(otp_code) != 6:
            raise forms.ValidationError('OTP must be exactly 6 digits.')
        
        return otp_code