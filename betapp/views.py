import os
import threading
from django.http import HttpResponse
from django.core.management import call_command
import json, base64, requests
from datetime import date
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Game, Payment
from .serializers import GameSerializer

try:
    from rest_framework import viewsets, status
    from rest_framework.decorators import action
    from rest_framework.response import Response
    from rest_framework.permissions import AllowAny
except ImportError:
    raise ImportError("Django Rest Framework is not installed. Run: pip install djangorestframework")



class BotViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], url_path='trigger')
    def trigger(self, request):
        token = request.query_params.get('token')
        if token != os.environ.get('BOT_SECRET_KEY'):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        def run_bot_task():
            call_command('run_bot')

        threading.Thread(target=run_bot_task).start()
        return Response({"status": "Bot started"}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_games_api(request):
    phone = request.GET.get('phone')
    # Check if a successful payment exists for this phone today
    has_paid = False
    if phone:
        # Standardize phone format if needed
        if phone.startswith('0'): phone = '254' + phone[1:]
        
        has_paid = Payment.objects.filter(
            phone_number=phone,
            status='SUCCESS',
            created_at__date=date.today()
        ).exists()

    games = Game.objects.all().order_by('-match_date')
    serializer = GameSerializer(games, many=True)
    
    return Response({
        'games': serializer.data,
        'has_paid_today': has_paid
    })

@api_view(['POST'])
def initiate_payment(request):
    raw_phone = request.data.get('phone', '')
    
    # Force the number into the exact 254... format before sending to PayHero
    # This removes any leading 0 or + and ensures it starts with 254
    clean_phone = raw_phone.strip().replace('+', '')
    if clean_phone.startswith('0'):
        clean_phone = '254' + clean_phone[1:]
    elif not clean_phone.startswith('254'):
        clean_phone = '254' + clean_phone

    # Final validation: Ensure it's exactly 12 digits (254 + 9 digits)
    if len(clean_phone) != 12:
        return Response({"error": "Invalid Kenya phone format. Use 2547XXXXXXXX"}, status=400)

    # Use the official PayHero v1 or v2 endpoint
    api_url = 'https://payhero.co.ke'
    
    payload = {
        "amount": 200,
        "phone_number": clean_phone, # Use the cleaned version here
        "channel_id": settings.PAYHERO_CHANNEL_ID,
        "provider": "m-pesa", # PayHero often requires the provider field
        "external_reference": f"PRO-{clean_phone[-4:]}-{int(time.time())}",
        "callback_url": "https://onrender.com"
    }

@csrf_exempt
def payhero_callback(request):
    """PayHero sends POST to this endpoint when payment is done"""
    if request.method == 'POST':
        data = json.loads(request.body)
        # PayHero sends 'external_reference' and 'status'
        ext_ref = data.get('external_reference')
        status = data.get('status') 

        try:
            payment = Payment.objects.get(external_reference=ext_ref)
            # PayHero status is usually "Success" or "Failed"
            payment.status = 'SUCCESS' if status.lower() == 'success' else 'FAILED'
            payment.save()
            return JsonResponse({'message': 'Verified'})
        except Payment.DoesNotExist:
            return JsonResponse({'error': 'Ref Not Found'}, status=404)
    return JsonResponse({'error': 'Invalid'}, status=400)
