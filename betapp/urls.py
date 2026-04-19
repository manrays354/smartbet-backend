from django.urls import path
from . import views


urlpatterns = [
    path('', views.get_games_api, name='get_games'), 
    path('initiate_payment/', views.initiate_payment, name='initiate_payment'),
    path('payhero_callback/', views.payhero_callback, name='payment_callback'),
]
