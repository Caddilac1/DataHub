from celery import shared_task
from authentication.models import DataBundleOrder
from .datamart_client import DataMartClient
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=None)
def recheck_datamart_status(self, order_id):
    logger.info(f"[TASK STARTED] recheck_datamart_status for order_id={order_id}")

    try:
        order = DataBundleOrder.objects.get(id=order_id)
        logger.debug(
            f"[DEBUG] Loaded Order {order.id} -> provider_order_id={order.provider_order_id}, status={order.status}"
        )
    except DataBundleOrder.DoesNotExist:
        logger.warning(f"[TASK STOPPED] Order ID {order_id} no longer exists.")
        return

    # 🔑 If provider_order_id missing, we cannot check status yet
    if not order.provider_order_id:
        logger.warning(
            f"[DEBUG] Order {order.id} has no provider_order_id yet. Retrying in 30s..."
        )
        raise self.retry(countdown=30)

    client = DataMartClient(settings.DATAMART_API_KEY)
    try:
        response = client.get_order_status(order.provider_order_id)
        status = response if isinstance(response, str) else None
        logger.debug(
            f"[DEBUG] DataMart returned status='{status}' for order {order.id}"
        )
    except Exception as e:
        logger.error(
            f"[ERROR] Failed to fetch status for order {order.id}: {str(e)}",
            exc_info=True,
        )
        raise self.retry(countdown=30)

    # 🔄 Update order based on status
    if status in ["completed", "failed"]:
        order.status = status
        order.save(update_fields=["status"])
        logger.info(f"[TASK COMPLETED] Order {order.id} marked as '{status}' ✅")
    elif status:
        if order.status != status:
            order.status = status
            order.save(update_fields=["status"])
            logger.debug(f"[DEBUG] Order {order.id} updated to '{status}'")
        logger.info(
            f"[DEBUG] Order {order.id} still pending/processing. Retrying in 30s..."
        )
        raise self.retry(countdown=30)
    else:
        logger.warning(
            f"[WARNING] No valid status returned for order {order.id}. Retrying in 30s..."
        )
        raise self.retry(countdown=30)
