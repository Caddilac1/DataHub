import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model
from threading import local

from .models import (
    AuditLog, 
    OTP, 
    DataBundleOrder, 
    Payment, 
    Bundle, 
    Telco
)

# Thread-local storage for request context and model instance cache
_thread_locals = local()
_original_instances = local()
_original_instances.cache = {}

# Logger for signal errors
logger = logging.getLogger(__name__)

User = get_user_model()


# ---------- Context Management ----------
def set_request_context(ip_address=None, user_agent=None, user=None):
    """Set request context for audit logging."""
    _thread_locals.ip_address = ip_address
    _thread_locals.user_agent = user_agent
    _thread_locals.current_user = user

def get_request_context():
    """Get current request context."""
    return {
        'ip_address': getattr(_thread_locals, 'ip_address', None),
        'user_agent': getattr(_thread_locals, 'user_agent', None),
        'current_user': getattr(_thread_locals, 'current_user', None)
    }

def clear_request_context():
    """Clear request context."""
    for attr in ['ip_address', 'user_agent', 'current_user']:
        if hasattr(_thread_locals, attr):
            delattr(_thread_locals, attr)


# ---------- Helper Functions ----------
def create_audit_log(action, user=None, details=None, ip_address=None, user_agent=None):
    """Create an audit log entry with error handling."""
    try:
        context = get_request_context()
        
        # Ensure the user is a valid User object or None
        log_user = user or context.get('current_user')
        if log_user and not isinstance(log_user, User):
            log_user = None

        AuditLog.objects.create(
            user=log_user,
            action=action,
            details=details or {},
            ip_address=ip_address or context.get('ip_address'),
            user_agent=user_agent or context.get('user_agent', '')
        )
    except Exception as e:
        logger.error(f"Failed to create audit log for action '{action}': {str(e)}")

def get_model_changes(instance, original_instance=None):
    """Get changed fields between model instances."""
    if not original_instance:
        return {}
    
    changes = {}
    for field in instance._meta.fields:
        field_name = field.name
        old_value = getattr(original_instance, field_name, None)
        new_value = getattr(instance, field_name, None)
        
        # Skip sensitive fields
        if field_name in ['password', 'hashed_code']:
            continue
            
        if old_value != new_value:
            changes[field_name] = {
                'old': str(old_value) if old_value is not None else None,
                'new': str(new_value) if new_value is not None else None
            }
    
    return changes


# ---------- Pre-Save Handlers to Cache Original Instances ----------
@receiver(pre_save, sender=User)
@receiver(pre_save, sender=Bundle)
@receiver(pre_save, sender=Telco)
@receiver(pre_save, sender=DataBundleOrder)
@receiver(pre_save, sender=Payment)
def cache_original_instance(sender, instance, **kwargs):
    """Caches the original instance before a save operation for change tracking."""
    if not hasattr(_original_instances, 'cache'):
        _original_instances.cache = {}
        
    if instance.pk:
        try:
            _original_instances.cache[instance.pk] = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            _original_instances.cache[instance.pk] = None


# ---------- Post-Save Handlers (Updated for Caching) ----------
@receiver(post_save, sender=User)
def user_post_save_handler(sender, instance, created, **kwargs):
    """Handle user creation and updates."""
    original = _original_instances.cache.pop(instance.pk, None)
    
    if created:
        create_audit_log(
            action='user_created',
            user=instance,
            details={
                'email': instance.email,
                'full_name': instance.full_name,
                'phone_number': instance.phone_number,
                'role': instance.role,
                'account_status': instance.account_status
            }
        )
    elif original:
        changes = get_model_changes(instance, original)
        if changes:
            if 'email_verified' in changes and changes['email_verified']['new'] == 'True':
                create_audit_log(
                    action='email_verified',
                    user=instance,
                    details={'email': instance.email, 'verified_at': str(timezone.now())}
                )
            
            if 'account_status' in changes:
                create_audit_log(
                    action='account_status_changed',
                    user=instance,
                    details={
                        'old_status': changes['account_status']['old'],
                        'new_status': changes['account_status']['new'],
                        'email': instance.email
                    }
                )
            
            if 'account_locked_until' in changes:
                if changes['account_locked_until']['new']:
                    create_audit_log(
                        action='account_locked',
                        user=instance,
                        details={'locked_until': changes['account_locked_until']['new'], 'email': instance.email}
                    )
                else:
                    create_audit_log(
                        action='account_unlocked',
                        user=instance,
                        details={'email': instance.email, 'unlocked_at': str(timezone.now())}
                    )
            
            create_audit_log(
                action='user_updated',
                user=instance,
                details={'changes': changes, 'email': instance.email}
            )


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """Handle successful user login."""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    if user.failed_login_attempts > 0:
        user.reset_failed_login_attempts()
    
    create_audit_log(
        action='user_login',
        user=user,
        details={'email': user.email, 'login_time': str(timezone.now()), 'session_key': request.session.session_key},
        ip_address=ip_address,
        user_agent=user_agent
    )


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """Handle user logout."""
    if user:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        create_audit_log(
            action='user_logout',
            user=user,
            details={'email': user.email, 'logout_time': str(timezone.now())},
            ip_address=ip_address,
            user_agent=user_agent
        )


@receiver(user_login_failed)
def user_login_failed_handler(sender, credentials, request, **kwargs):
    """Handle failed login attempts."""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    user = None
    email = credentials.get('email') or credentials.get('username')
    if email:
        try:
            user = User.objects.get(email=email)
            user.increment_failed_login()
        except User.DoesNotExist:
            pass
    
    create_audit_log(
        action='login_failed',
        user=user,
        details={
            'attempted_email': email,
            'failure_time': str(timezone.now()),
            'credentials_provided': list(credentials.keys())
        },
        ip_address=ip_address,
        user_agent=user_agent
    )


# ---------- OTP-Related Signals ----------
@receiver(post_save, sender=OTP)
def otp_post_save_handler(sender, instance, created, **kwargs):
    """Handle OTP creation and updates."""
    if created:
        create_audit_log(
            action='otp_generated',
            user=instance.user,
            details={
                'otp_type': instance.otp_type,
                'expires_at': str(instance.expires_at),
                'max_attempts': instance.max_attempts,
                'user_email': instance.user.email
            },
            ip_address=instance.ip_address,
            user_agent=instance.user_agent
        )
    else:
        if instance.status == 'used':
            create_audit_log(
                action='otp_verified',
                user=instance.user,
                details={
                    'otp_type': instance.otp_type,
                    'verified_at': str(instance.used_at),
                    'attempts_used': instance.attempts,
                    'user_email': instance.user.email
                },
                ip_address=instance.ip_address,
                user_agent=instance.user_agent
            )
        elif instance.status in ['expired', 'invalidated']:
            create_audit_log(
                action='otp_failed',
                user=instance.user,
                details={
                    'otp_type': instance.otp_type,
                    'status': instance.status,
                    'attempts_used': instance.attempts,
                    'max_attempts': instance.max_attempts,
                    'user_email': instance.user.email
                },
                ip_address=instance.ip_address,
                user_agent=instance.user_agent
            )


# ---------- Order-Related Signals ----------
@receiver(post_save, sender=DataBundleOrder)
def order_post_save_handler(sender, instance, created, **kwargs):
    """Handle order creation and updates."""
    original = _original_instances.cache.pop(instance.pk, None)

    if created:
        create_audit_log(
            action='order_created',
            user=instance.user,
            details={
                'order_id': instance.id,
                'telco': instance.telco.name,
                'bundle': f"{instance.bundle.name} - {instance.bundle.size_mb}MB",
                'phone_number': instance.phone_number,
                'bundle_price': str(instance.bundle.price)
            },
            ip_address=instance.ip_address,
            user_agent=instance.user_agent
        )
    elif original and original.status != instance.status:
        create_audit_log(
            action='order_status_changed',
            user=instance.user,
            details={
                'order_id': instance.id,
                'old_status': original.status,
                'new_status': instance.status,
                'phone_number': instance.phone_number,
                'provider_order_id': instance.provider_order_id
            }
        )


# ---------- Payment-Related Signals ----------
@receiver(post_save, sender=Payment)
def payment_post_save_handler(sender, instance, created, **kwargs):
    """Handle payment creation and updates."""
    original = _original_instances.cache.pop(instance.pk, None)

    if created:
        create_audit_log(
            action='payment_initiated',
            user=instance.order.user,
            details={
                'payment_id': instance.id,
                'order_id': instance.order.id,
                'amount': str(instance.amount),
                'reference': instance.reference,
                'phone_number': instance.order.phone_number
            },
            ip_address=instance.ip_address,
            user_agent=instance.user_agent
        )
    elif original and original.status != instance.status:
        action_map = {
            'success': 'payment_completed',
            'failed': 'payment_failed',
            'refunded': 'payment_refunded',
            'cancelled': 'payment_cancelled'
        }
        
        action = action_map.get(instance.status, 'payment_status_changed')
        
        create_audit_log(
            action=action,
            user=instance.order.user,
            details={
                'payment_id': instance.id,
                'order_id': instance.order.id,
                'amount': str(instance.amount),
                'reference': instance.reference,
                'old_status': original.status,
                'new_status': instance.status,
                'paid_at': str(instance.paid_at) if instance.paid_at else None
            }
        )


# ---------- Bundle & Telco Signals ----------
@receiver(post_save, sender=Bundle)
def bundle_post_save_handler(sender, instance, created, **kwargs):
    """Handle bundle creation and updates."""
    context = get_request_context()
    original = _original_instances.cache.pop(instance.pk, None)
    
    if created:
        create_audit_log(
            action='bundle_created',
            user=context.get('current_user'),
            details={
                'bundle_id': instance.id,
                'telco': instance.telco.name,
                'name': instance.name,
                'size_mb': instance.size_mb,
                'price': str(instance.price)
            }
        )
    elif original:
        changes = get_model_changes(instance, original)
        
        if 'price' in changes:
            create_audit_log(
                action='bundle_price_changed',
                user=context.get('current_user'),
                details={
                    'bundle_id': instance.id,
                    'telco': instance.telco.name,
                    'bundle_name': instance.name,
                    'old_price': changes['price']['old'],
                    'new_price': changes['price']['new']
                }
            )
        
        if 'is_active' in changes:
            action = 'bundle_activated' if instance.is_active else 'bundle_deactivated'
            create_audit_log(
                action=action,
                user=context.get('current_user'),
                details={
                    'bundle_id': instance.id,
                    'telco': instance.telco.name,
                    'bundle_name': instance.name
                }
            )


@receiver(post_save, sender=Telco)
def telco_post_save_handler(sender, instance, created, **kwargs):
    """Handle telco creation and updates."""
    context = get_request_context()
    original = _original_instances.cache.pop(instance.pk, None)
    
    if created:
        create_audit_log(
            action='telco_created',
            user=context.get('current_user'),
            details={
                'telco_id': instance.id,
                'name': instance.name,
                'code': instance.code
            }
        )
    elif original and original.is_active != instance.is_active:
        action = 'telco_activated' if instance.is_active else 'telco_deactivated'
        create_audit_log(
            action=action,
            user=context.get('current_user'),
            details={
                'telco_id': instance.id,
                'name': instance.name,
                'code': instance.code
            }
        )


# ---------- Utility Functions ----------
def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ---------- Custom Signal for Manual Audit Logging ----------
def log_custom_action(action, user=None, details=None, request=None):
    """
    Manually log custom actions not covered by automatic signals.
    """
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    create_audit_log(
        action=action,
        user=user,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )


# ---------- Cleanup Signal (Optional) ----------
@receiver(post_save, sender=AuditLog)
def audit_log_cleanup_handler(sender, instance, created, **kwargs):
    """
    Optional: Trigger cleanup of old audit logs.
    You might want to run this as a periodic task instead.
    """
    if created:
        import random
        if random.randint(1, 100) == 1:
            try:
                cutoff_date = timezone.now() - timezone.timedelta(days=365)
                old_logs_count = AuditLog.objects.filter(created_at__lt=cutoff_date).count()
                if old_logs_count > 0:
                    AuditLog.objects.filter(created_at__lt=cutoff_date).delete()
                    logger.info(f"Cleaned up {old_logs_count} old audit log entries")
            except Exception as e:
                logger.error(f"Failed to cleanup old audit logs: {str(e)}")