from .views import BotViewSet 
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'bot', BotViewSet, basename='bot')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', views.get_games_api, name='get_games'), 
    path('initiate_payment/', views.initiate_payment, name='initiate_payment'),
    path('payhero_callback/', views.payhero_callback, name='payment_callback'),
]
