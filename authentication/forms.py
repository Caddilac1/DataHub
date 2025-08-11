# authentication/forms.py

from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser

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