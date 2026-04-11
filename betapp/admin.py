from django.contrib import admin
from .models import Game

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('title', 'match_date', 'is_premium', 'price')
    list_filter = ('is_premium', 'match_date')
    search_fields = ('title',)