# home/services.py
import requests
from django.conf import settings


PAYSTACK_API_BASE_URL = 'https://api.paystack.co'

def initialize_paystack_payment(email, amount, reference, callback_url):
    """Initializes a new transaction with Paystack."""
    url = f'{PAYSTACK_API_BASE_URL}/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {settings.TEST_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        'email': email,
        'amount': int(amount) * 100,  # Paystack amount is in kobo (pennies)
        'reference': reference,
        'callback_url': callback_url,
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def verify_paystack_payment(reference):
    """Verifies a transaction with Paystack."""
    url = f'{PAYSTACK_API_BASE_URL}/transaction/verify/{reference}'
    headers = {
        'Authorization': f'Bearer {settings.TEST_SECRET_KEY}',
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()