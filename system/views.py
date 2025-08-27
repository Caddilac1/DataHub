from django.shortcuts import render
from django.contrib.auth import login
import json
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages
from django.db.models import Count, Q
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from authentication.models import *
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from authentication.models import Bundle, DataBundleOrder, Payment
from .services import initialize_paystack_payment, verify_paystack_payment
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Create your views here.


class HomeView(TemplateView):
    template_name = 'home/home.html'

    def get(self, request, *args, **kwargs):
        bundles = Bundle.objects.select_related('telco').filter(is_agent_bundle=False).order_by('telco__name', 'size_mb')
        data_plans = {}

        for bundle in bundles:
            size_display = f"{bundle.size_mb // 1000}GB" if bundle.size_mb >= 1000 else f"{bundle.size_mb}MB"
            validity = "Non-Expiry" if bundle.telco.name.lower() in ['mtn', 'telecel'] else "30 days"

            provider_name = bundle.telco.name
            if provider_name not in data_plans:
                data_plans[provider_name] = []

            data_plans[provider_name].append({
                'id': bundle.id,
                'size': size_display,
                'price': f"GH₵ {bundle.price:.2f}",
                'validity': validity,
                'code': bundle.telco.code
            })

        context = {
            'data_plans': data_plans,
            'paystack_public_key': settings.TEST_PUBLIC_KEY,
            'user': request.user
        }

        return render(request, self.template_name, context)

# Create your views here.







class TelcoStockListView(ListView):
    model = Telco
    template_name = "telcos.html"
    context_object_name = "telcos"

    def get_queryset(self):
        # Annotate each Telco with counts of in-stock and out-of-stock bundles
        return Telco.objects.annotate(
            total_bundles=Count('bundle'),
            in_stock_bundles=Count('bundle', filter=Q(bundle__is_instock=True)),
            out_stock_bundles=Count('bundle', filter=Q(bundle__is_instock=False)),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for telco in context["telcos"]:
            if telco.in_stock_bundles == telco.total_bundles and telco.total_bundles > 0:
                telco.stock_status = "in-stock"
            elif telco.in_stock_bundles > 0:
                telco.stock_status = "limited"
            else:
                telco.stock_status = "out-of-stock"
        return context






import logging

logger = logging.getLogger(__name__)

class TestHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home/test_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        logger.debug("[TestHomeView] Fetching non-agent bundles...")
        bundles = Bundle.objects.select_related('telco').filter(is_agent_bundle=False).order_by('telco__name', 'size_mb')
        logger.debug(f"[TestHomeView] Total bundles fetched: {bundles.count()}")

        data_plans = {}
        telco_stock_status = {}  # <-- new dict for telco stock states

        for bundle in bundles:
            size_display = f"{bundle.size_mb // 1000}GB" if bundle.size_mb >= 1000 else f"{bundle.size_mb}MB"
            validity = "Non-Expiry" if bundle.telco.name.lower() in ['mtn', 'telecel'] else "30 days"

            provider_name = bundle.telco.name
            if provider_name not in data_plans:
                data_plans[provider_name] = []
                telco_stock_status[provider_name] = []
                logger.debug(f"[TestHomeView] Initializing telco entry: {provider_name}")

            # Add bundle info
            data_plans[provider_name].append({
                'id': bundle.id,
                'size': size_display,
                'price': f"{bundle.price:.2f}",
                'validity': validity,
                'code': bundle.telco.code,
                'is_instock': bundle.is_instock
            })

            logger.debug(
                f"[TestHomeView] Bundle added | Telco={provider_name}, Size={size_display}, "
                f"Price={bundle.price:.2f}, Stock={bundle.is_instock}"
            )

            # Track stock availability for this telco
            telco_stock_status[provider_name].append(bundle.is_instock)

        # Determine stock summary per telco
        telco_summary = {}
        for telco, stocks in telco_stock_status.items():
            if all(stocks):
                telco_summary[telco] = "in-stock"
            elif any(stocks):
                telco_summary[telco] = "limited-stock"
            else:
                telco_summary[telco] = "out-of-stock"

            logger.debug(f"[TestHomeView] Telco summary | {telco}: {telco_summary[telco]}")

        # Fetch user orders
        orders = DataBundleOrder.objects.filter(user=self.request.user).order_by('-created_at')
        logger.debug(f"[TestHomeView] Orders for {self.request.user}: {orders.count()}")

        paginator = Paginator(orders, 15)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        logger.debug(f"[TestHomeView] Paginated orders | Page={page_number}, Objects={len(page_obj)}")

        # Fetch today’s recent orders
        today = timezone.now().date()
        rec_orders = DataBundleOrder.objects.filter(created_at__date=today).order_by('-created_at')
        logger.debug(f"[TestHomeView] Recent orders today ({today}): {rec_orders.count()}")

        # Update context
        context.update({
            'data_plans': data_plans,
            'telco_summary': telco_summary,
            'paystack_public_key': settings.TEST_PUBLIC_KEY,
            'user': self.request.user,
            'orders': orders,
            'rec_orders': rec_orders,
            'page_obj': page_obj,
            'telcos': Telco.objects.all()
        })

        logger.debug("[TestHomeView] Context successfully prepared.")

        return context



# home/views.py



# --- New Class-Based View for Payment Logic ---
class PaymentView(LoginRequiredMixin, View):
    
    def post(self, request, *args, **kwargs):
        """
        Handles the POST request to initiate a new Paystack payment.
        This replaces the old `initiate_payment` function.
        """
        bundle_id = request.POST.get('bundle_id')
        phone_number = request.POST.get('phone_number')
        
        if not bundle_id or not phone_number:
            return JsonResponse({'status': 'error', 'message': 'Missing bundle ID or phone number'}, status=400)

        try:
            with transaction.atomic():
                bundle = get_object_or_404(Bundle, pk=bundle_id)
                logger.info(f"Successfully retrieved bundle with ID: {bundle_id}")
                user = request.user
                
                # Create the order first 
                order = DataBundleOrder.objects.create(
                    user=user,
                    telco=bundle.telco,
                    bundle=bundle,
                    phone_number=phone_number,
                    status='pending',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                logger.info(f"Order {order.id} created successfully.")
                
                # Generate a unique reference ID for the Paystack transaction
                reference = str(uuid.uuid4())
                
                # Create the payment record linked to the order
                logger.info(f"Creating payment record for order {order.id}")
                payment = Payment.objects.create(
                    order=order,
                    amount=bundle.price,
                    reference=reference,
                    status='pending'
                )
                logger.info(f"Payment record created: {payment.id}")

                # Build the callback URL for Paystack to redirect to
                callback_url = request.build_absolute_uri(reverse('payment_callback'))
                logger.info(f"Initializing Paystack payment for user {user.email}, reference {reference}.")
                
                paystack_response = initialize_paystack_payment(
                    email=user.email,
                    amount=payment.amount,
                    reference=reference,
                    callback_url=callback_url
                )
                
                return JsonResponse({'status': 'success', 'authorization_url': paystack_response['data']['authorization_url']})
            
        except Exception as e:
            logger.error(f"Error initiating payment: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    def get(self, request, *args, **kwargs):
        """
        Handles the GET request from Paystack after a payment attempt.
        This replaces the old `paystack_callback` function.
        """
        user = request.user
        reference = request.GET.get('reference')
        if not reference:
            return redirect(reverse('test_home') + '?payment_status=failed&message=Invalid payment reference')
            
        try:
            paystack_response = verify_paystack_payment(reference)
            
            if paystack_response['data']['status'] == 'success':
                with transaction.atomic():
                    payment = get_object_or_404(Payment, reference=reference)
                    order = payment.order
                    
                    payment.status = 'success'
                    payment.paid_at = paystack_response['data']['paid_at']
                    payment.save()
                    
                    order.status = 'paid' # 'paid' status before fulfillment begins
                    order.save()
                    recheck_datamart_status(order.id)
                    
                    # Log successful payment for internal records
                    logger.info(f"Payment successful for order {order.id}. Reference: {reference}")
                if user.role == 'customer':

                    messages.success(request, f"Payment successful for order {order.id}. Your data bundle will be processed shortly.")
                    return redirect(reverse('home') + f'?payment_status=success&order_id={order.id}')
                elif user.role == 'agent':
                    messages.success(request, f"Payment successful for order {order.id}. The data bundle will be processed shortly.")
                    return redirect(reverse('agent_home_page') + f'?payment_status=success&order_id={order.id}')

                else:
                    messages.success(request, f"Payment successful for order {order.id}. The data bundle will be processed shortly.")
                    return redirect(reverse('home') + f'?payment_status=success&order_id={order.id}')   
                
            else:
                payment = get_object_or_404(Payment, reference=reference)
                order = payment.order
                
                payment.status = 'failed'
                payment.save()
                
                order.status = 'failed'
                order.save()
                
                logger.warning(f"Payment failed for order {order.id}. Paystack status: {paystack_response['data']['status']}")
                
                return redirect(reverse('test_home') + '?payment_status=failed')
                
        except Exception as e:
            logger.error(f"Error during payment verification for reference {reference}: {e}", exc_info=True)
            return redirect(reverse('home') + f'?payment_status=error&message={str(e)}')
        



class GuestOrderView(View):
    def post(self, request, *args, **kwargs):
        phone_number = request.POST.get('phone_number')
        bundle_id = request.POST.get('bundle_id')

        if not all([phone_number, bundle_id]):
            return JsonResponse({'status': 'error', 'message': 'Missing phone number or bundle ID.'}, status=400)

        try:
            bundle = get_object_or_404(Bundle, pk=bundle_id)

            # Create a guest user based on the phone number
            # This is crucial for linking the order to a user object
            guest_user, created = CustomUser.objects.get_or_create(
                phone_number=phone_number,
                defaults={
                    'full_name': 'Guest User',
                    'email': f'guest_{uuid.uuid4().hex[:10]}@datahub.com',
                    'role': 'customer',
                    'account_status': 'active',
                    'email_verified': True
                }
            )

            with transaction.atomic():
                order = DataBundleOrder.objects.create(
                    user=guest_user,
                    telco=bundle.telco,
                    bundle=bundle,
                    phone_number=phone_number,
                    status='pending',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                reference = str(uuid.uuid4())
                
                payment = Payment.objects.create(
                    order=order,
                    amount=bundle.price,
                    reference=reference,
                    status='pending'
                )
                
                callback_url = request.build_absolute_uri(reverse('payment_callback'))

                paystack_response = initialize_paystack_payment(
                    email=guest_user.email,
                    amount=payment.amount,
                    reference=reference,
                    callback_url=callback_url
                )

                if paystack_response.get('status'):
                    return JsonResponse({'status': 'success', 'authorization_url': paystack_response['data']['authorization_url']})
                else:
                    raise Exception("Failed to initialize payment with gateway.")

        except Exception as e:
            logger.error(f"Error during guest order creation: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)