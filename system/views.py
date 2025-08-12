from django.shortcuts import render
from django.contrib.auth import login
import json
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages
from django.db.models import Count, Q
from django.views.generic import ListView
from django.views.generic import TemplateView
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
        bundles = Bundle.objects.select_related('telco').all().order_by('telco__name', 'size_mb')
        data_plans = {}

        for bundle in bundles:
            size_display = f"{bundle.size_mb // 1000}GB" if bundle.size_mb >= 1000 else f"{bundle.size_mb}MB"
            validity = "Non-Expiry" if bundle.telco.name.lower() in ['mtn', 'telecel'] else "30 days"

            provider_name = bundle.telco.name
            if provider_name not in data_plans:
                data_plans[provider_name] = []

            data_plans[provider_name].append({
                'size': size_display,
                'price': f"GH₵ {bundle.price:.2f}",
                'validity': validity,
                'code': bundle.telco.code
            })

        data_plans_json = json.dumps(data_plans)

        return self.render_to_response({
            'data_plans': data_plans,
            'data_plans_json': data_plans_json,
            'user': request.user  
        })



# Create your views here.




"""class HomeView(View):
    template_name = 'home/home.html'

    def get(self, request):
        context = {}
        return render(request, self.template_name, context)

"""


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






class TestHomeView(LoginRequiredMixin, TemplateView):
    """
    A class-based view to display the home page with bundles categorized by telco,
    without using JSON for client-side rendering.
    """
    template_name = 'home/test_home.html'

    def get_context_data(self, **kwargs):
        """
        Populate the context with a structured dictionary of data plans.
        """
        context = super().get_context_data(**kwargs)
        
        bundles = Bundle.objects.select_related('telco').all().order_by('telco__name', 'size_mb')
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
                'price': f"{bundle.price:.2f}",  # Keep price as string for display
                'validity': validity,
                'code': bundle.telco.code
            })
        
        context['data_plans'] = data_plans
        context['paystack_public_key'] = settings.TEST_PUBLIC_KEY  # Use the test public key for client-side integration
        context['user'] = self.request.user  # Pass the user object to the template for
        
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
                
                # Generate a unique reference ID for the Paystack transaction
                reference = str(uuid.uuid4())
                
                # Create the payment record linked to the order
                payment = Payment.objects.create(
                    order=order,
                    amount=bundle.price,
                    reference=reference,
                    status='pending'
                )

                # Build the callback URL for Paystack to redirect to
                callback_url = request.build_absolute_uri(reverse('payment_callback'))
                
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
                    
                    # Log successful payment for internal records
                    logger.info(f"Payment successful for order {order.id}. Reference: {reference}")
                    
                return redirect(reverse('test_home') + f'?payment_status=success&order_id={order.id}')
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
            return redirect(reverse('test_home') + f'?payment_status=error&message={str(e)}')