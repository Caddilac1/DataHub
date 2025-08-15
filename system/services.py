# home/services.py
import requests
from authentication.models import DataBundleOrder, Payment, SystemConfiguration
from django.conf import settings
from .datamart_client import DataMartClient
import logging

logger = logging.getLogger(__name__)

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
    """
    Handle successful payment with admin-controlled API triggering.
    
    Args:
        order_id (str): The order ID to process
        
    Returns:
        dict: Result of the operation including API call status
    """
    try:
        order = DataBundleOrder.objects.get(id=order_id)
    except DataBundleOrder.DoesNotExist:
        logger.error(f"Order with ID {order_id} not found")
        return {'success': False, 'error': 'Order not found'}
    
    # Update order status to completed (always done regardless of API setting)
    order.status = 'completed'
    order.save()
    
    # Update payment status if it exists
    try:
        payment = Payment.objects.get(order=order)
        payment.status = 'success'
        payment.save()
        logger.info(f"Payment for order {order_id} marked as successful")
    except Payment.DoesNotExist:
        logger.warning(f"No payment record found for order {order_id}")
    
    # Check if auto API trigger is enabled
    is_auto_trigger_enabled = SystemConfiguration.is_auto_api_trigger_enabled()
    
    result = {
        'success': True,
        'order_id': order_id,
        'order_status': 'completed',
        'api_triggered': False,
        'api_enabled': is_auto_trigger_enabled
    }
    
    if is_auto_trigger_enabled:
        # Trigger the DataMart API
        api_result = trigger_datamart_api(order)
        result.update({
            'api_triggered': True,
            'api_result': api_result
        })
        logger.info(f"DataMart API triggered for order {order_id}: {api_result}")
    else:
        logger.info(f"DataMart API not triggered for order {order_id} - feature disabled by admin")
    
    return result

def trigger_datamart_api(order):
    """
    Trigger the DataMart API for a given order.
    
    Args:
        order (DataBundleOrder): The order to process
        
    Returns:
        dict: Result of the API call
    """
    phone_number = order.phone_number
    network_code = order.telco.code
    bundle_size_mb = order.bundle.size_mb
    bundle_size_gb = f"{bundle_size_mb / 1000:g}"
    
    try:
        client = DataMartClient(settings.DATAMART_API_KEY)
        response = client.purchase_data(phone_number, network_code, bundle_size_gb)
        
        # Update order with provider information if available
        if hasattr(response, 'get') and response.get('order_id'):
            order.provider_order_id = response.get('order_id')
            order.provider_status = response.get('status', 'processing')
            order.save()
        
        return {
            'success': True,
            'response': response,
            'message': 'DataMart API call successful'
        }
    except Exception as e:
        logger.error(f"DataMart API call failed for order {order.id}: {str(e)}")
        # Mark order as failed if API call fails
        order.status = 'failed'
        order.save()
        
        return {
            'success': False,
            'error': str(e),
            'message': 'DataMart API call failed'
        }

def manually_trigger_api_for_order(order_id, admin_user):
    """
    Manually trigger DataMart API for a specific order (admin function).
    
    Args:
        order_id (str): The order ID to process
        admin_user: The admin user triggering the action
        
    Returns:
        dict: Result of the operation
    """
    if admin_user.role != 'admin':
        return {
            'success': False,
            'error': 'Only admins can manually trigger API calls'
        }
    
    try:
        order = DataBundleOrder.objects.get(id=order_id)
    except DataBundleOrder.DoesNotExist:
        return {
            'success': False,
            'error': 'Order not found'
        }
    
    if order.status != 'completed':
        return {
            'success': False,
            'error': 'Order must be completed before triggering API'
        }
    
    api_result = trigger_datamart_api(order)
    
    # Log this manual action
    logger.info(f"Manual API trigger by admin {admin_user.email} for order {order_id}")
    
    return {
        'success': True,
        'message': 'Manual API trigger completed',
        'api_result': api_result,
        'triggered_by': admin_user.email
    }