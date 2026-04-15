import json, base64, requests
from datetime import date
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Game, Payment
from .serializers import GameSerializer

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
    phone = request.data.get('phone')
    if not phone:
        return Response({"error": "Phone number is required"}, status=400)
    
    # Format phone to 254...
    if phone.startswith('0'): phone = '254' + phone[1:]
    
    amount = 200
    # Unique reference: PRO-PhoneLast4-Timestamp
    external_ref = f"PRO-{phone[-4:]}-{int(date.today().strftime('%y%m%d%H%M'))}"
    
    Payment.objects.create(
        external_reference=external_ref,
        phone_number=phone,
        amount=amount,
        status='PENDING'
    )
    
    # PayHero V2 API credentials from settings.py
    api_url = 'https://payhero.co.ke'
    auth_str = f"{settings.PAYHERO_API_USERNAME}:{settings.PAYHERO_API_PASSWORD}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    
    payload = {
        "amount": amount,
        "phone_number": phone,
        "channel_id": settings.PAYHERO_CHANNEL_ID,
        "external_reference": external_ref,
        "callback_url": "https://onrender.com" 
    }
    
    headers = {'Authorization': f'Basic {b64_auth}', 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        res_data = response.json()
        if response.status_code in [200, 201] and res_data.get('success'):
            return Response({"message": "STK Push Sent", "reference": external_ref}, status=200)
        return Response({"error": res_data.get('status', 'Provider error')}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

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
