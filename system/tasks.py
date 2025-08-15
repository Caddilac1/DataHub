from celery import shared_task
from authentication.models import DataBundleOrder
from .datamart_client import DataMartClient
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=None)  # unlimited retries
def recheck_datamart_status(self, order_id):
    logger.info(f"[TASK STARTED] recheck_datamart_status for order_id={order_id}")
    print(f"DEBUG: Task triggered for order_id={order_id}")

    try:
        order = DataBundleOrder.objects.get(id=order_id)
        logger.info(f"DEBUG: Found order {order.id} with current status '{order.status}'")
    except DataBundleOrder.DoesNotExist:
        logger.warning(f"[TASK STOPPED] Order ID {order_id} no longer exists.")
        return  # Stop if order no longer exists
    
    client = DataMartClient(settings.DATAMART_API_KEY)
    status = client.get_order_status(order.datamart_order_id)
    logger.info(f"DEBUG: DataMart returned status '{status}' for order {order.id}")

    if status == 'success':
        order.status = 'completed'
        order.save(update_fields=['status'])
        logger.info(f"[TASK COMPLETED] Order {order.id} marked as 'completed'")

    elif status == 'failed':
        order.status = 'failed'
        order.save(update_fields=['status'])
        logger.info(f"[TASK COMPLETED] Order {order.id} marked as 'failed'")

    elif status == 'processing':
        if order.status != 'processing':
            order.status = 'processing'
            order.save(update_fields=['status'])
            logger.info(f"DEBUG: Order {order.id} updated to 'processing'")
        logger.info(f"DEBUG: Order {order.id} still processing. Retrying in 60s...")
        raise self.retry(countdown=60)

    else:  # status is pending or unknown
        logger.info(f"DEBUG: Order {order.id} still pending/unknown. Retrying in 60s...")
        raise self.retry(countdown=60)
