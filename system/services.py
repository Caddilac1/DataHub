# home/services.py
import requests
from authentication.models import DataBundleOrder, Payment
from django.conf import settings
from .datamart_client import DataMartClient


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
        'amount': int(amount * 100),  # Paystack amount is in kobo (pennies)
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



def handle_successful_payment(order_id):

    try:
        order = DataBundleOrder.objects.get(id=order_id)
    except DataBundleOrder.DoesNotExist:
        return

    phone_number = order.phone_number
    network_code = order.telco.code
    bundle_size_mb = order.bundle.size_mb
    bundle_size_gb = f"{bundle_size_mb / 1000:g}"

    client = DataMartClient(settings.DATAMART_API_KEY)
    response = client.purchase_data(phone_number, network_code, bundle_size_gb)

