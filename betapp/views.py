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
    """
    Returns games and checks if the current user has paid today 
    based on their phone number (sent as a query param).
    """
    phone = request.GET.get('phone')
    today_str = date.today().strftime('%Y-%m-%d')
    
    # Check if this phone number has a SUCCESSFUL payment for today
    has_paid = False
    if phone:
        has_paid = Payment.objects.filter(
            phone_number=phone,
            status='SUCCESS',
            created_at__date=date.today() # Requires a 'created_at' field in model
        ).exists()

    games = Game.objects.all().order_by('-match_date')
    serializer = GameSerializer(games, many=True)
    
    return Response({
        'games': serializer.data,
        'has_paid_today': has_paid
    })

@api_view(['POST'])
def initiate_payment(request):
    """Handles STK Push via PayHero API"""
    phone = request.data.get('phone')
    amount = 200
    external_ref = f"PRO-{date.today().strftime('%y%m%d')}-{phone}"
    
    # 1. Create Local Pending Record
    payment, created = Payment.objects.get_or_create(
        external_reference=external_ref,
        defaults={'phone_number': phone, 'amount': amount, 'status': 'PENDING'}
    )
    
    # 2. PayHero API Setup
    api_url = 'https://payhero.co.ke' # Ensure this is the correct endpoint
    auth_str = f"{settings.PAYHERO_API_USERNAME}:{settings.PAYHERO_API_PASSWORD}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    
    payload = {
        "channel_id": settings.PAYHERO_CHANNEL_ID,
        "amount": amount,
        "phone_number": phone,
        "external_reference": external_ref,
        "callback_url": request.build_absolute_uri('/payment-callback/')
    }
    
    headers = {'Authorization': f'Basic {b64_auth}', 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            return Response({"message": "STK Push Sent", "status": "pending"}, status=200)
        return Response({"error": "Provider error"}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@csrf_exempt
def payhero_callback(request):
    """Updates payment status when PayHero confirms the transaction"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # PayHero status values: 'SUCCESS', 'FAILED', or 'QUEUED'
            ext_ref = data.get('ExternalReference')
            status = data.get('status') 

            payment = Payment.objects.get(external_reference=ext_ref)
            payment.status = status
            # If successful, you could log additional data like M-Pesa receipt
            payment.save()
            return JsonResponse({'message': 'Status Updated'})
        except Payment.DoesNotExist:
            return JsonResponse({'error': 'Reference not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

