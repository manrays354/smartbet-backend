import json
import base64
import requests
from datetime import date
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Game, Payment
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Game
from .serializers import GameSerializer


@api_view(['GET'])
def get_games_api(request):
    games = Game.objects.all().order_by('-match_date')
    serializer = GameSerializer(games, many=True)
    return Response(serializer.data)
    if not has_paid_today:
        paid_record = Payment.objects.filter(
            external_reference__contains=pass_ref,
            status='SUCCESS'
        ).exists()
        if paid_record:
            has_paid_today = True
            request.session[f'paid_{today_str}'] = True

    return render(request, 'dashboard.html', {
        'games': all_games,
        'has_paid_today': has_paid_today,
        'daily_price': 200
    })

def initiate_payment(request):
    if request.method == 'POST':
        phone = request.POST.get('phone') # Matches HTML name="phone"
        amount = 200
        today_tag = date.today().strftime('%Y-%m-%d')
        external_ref = f"PASS-{today_tag}-{phone}"
        
        # 1. Create Local Record
        payment = Payment.objects.create(
            phone_number=phone,
            amount=amount,
            external_reference=external_ref,
            status="PENDING"
        )
        
        # 2. PayHero API Setup
        api_url = 'https://payhero.co.ke'
        auth_str = f"{settings.PAYHERO_API_USERNAME}:{settings.PAYHERO_API_PASSWORD}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        
        payload = {
            "channel_id": settings.PAYHERO_CHANNEL_ID,
            "amount": amount,
            "phone_number": phone,
            "external_reference": external_ref,
            "provider": "m-pesa",
            "callback_url": request.build_absolute_uri('/payment-callback/')
        }
        
        headers = {'Authorization': f'Basic {b64_auth}', 'Content-Type': 'application/json'}
        
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            if response.status_code in [200, 201]:
                data = response.json()
                payment.checkout_request_id = data.get('CheckoutRequestID', '')
                payment.save()
        except Exception as e:
            print(f"Connection Error: {e}")
            
    return redirect('home')

@csrf_exempt
def payhero_callback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # PayHero = uses "ExternalReference" and "status" in callback
            ext_ref = data.get('ExternalReference')
            status = data.get('status') 

            payment = Payment.objects.get(external_reference=ext_ref)
            payment.status = status # Will be 'SUCCESS' or 'FAILED'
            payment.save()
            return JsonResponse({'message': 'Updated'})
        except (Payment.DoesNotExist, Exception):
            return JsonResponse({'error': 'Invalid'}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)





