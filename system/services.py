# home/services.py
import requests
import json
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

    # Prepare request values
    phone_number = order.phone_number
    network_code = order.telco.code  # make sure this matches DataMart's expected value
    bundle_size_mb = order.bundle.size_mb
    bundle_size_gb = f"{bundle_size_mb / 1000:g}"  # Convert MB → GB as string

    client = DataMartClient(settings.DATAMART_API_KEY)

    # Step 1: Call DataMart API
    try:
        response_data = client.purchase_data(
            phone_number=phone_number,
            network=network_code,
            capacity=bundle_size_gb
        )
    except Exception as e:
        # API call failed → mark as waiting
        print(f"[Order Sync] API request failed: {e}")
        order.status = "failed"
        order.save(update_fields=["status"])
        return

    # Debug print full response
    print(f"DataMart API full response: {json.dumps(response_data, indent=2)}")

    # Step 2: Extract important details from API response
    try:
        api_data = (
            response_data
            .get("data", {})
            .get("apiResponse", {})
            .get("data", {})
        )

        
        provider_order_id = api_data.get("ref")
        provider_status = api_data.get("status")  # The important status

        if provider_order_id and ref and provider_status:
            order.provider_order_id = ref
            order.status = provider_status
            order.save(update_fields=["provider_order_id", "status"])
            print(f"[Order Sync] Saved ID={ref}, status={provider_status}")
        else:
            # Missing necessary fields → waiting
            print("[Order Sync] Missing required fields in API response.")
            order.status = "failed"
            order.save(update_fields=["status"])

    except Exception as e:
        print(f"[Order Sync] Failed to parse API response: {e}")
        order.status = "failed"
        order.save(update_fields=["status"])

