from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent'),
        ('admin', 'Admin'),
    ]

    username = None  # remove username field
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)  # make sure email is unique
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = ['full_name', 'phone_number']  

    def __str__(self):
        return self.email
