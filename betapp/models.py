from django.db import models
from django.core.exceptions import ValidationError

class Game(models.Model):
    PREDICTION_CHOICES = [
        ('1', 'Home Win (1)'), 
        ('X', 'Draw (X)'), 
        ('2', 'Away Win (2)'),
        ('OV25', 'Over 2.5'), 
        ('UN25', 'Under 2.5'), 
        ('BTTS', 'Both Teams Score'),
    ]

    title = models.CharField(max_length=200)
    match_date = models.DateTimeField()
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Professional Odds & Stake
    odds = models.DecimalField(max_digits=5, decimal_places=2, help_text="e.g. 1.85")
    bookmaker = models.CharField(max_length=50, blank=True, help_text="e.g. Bet365, 1xBet")
    
    # Logic Fields
    predicted_outcome = models.CharField(max_length=10, choices=PREDICTION_CHOICES)
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    is_finished = models.BooleanField(default=False)
    
    # These fields now have defaults to prevent the Render EOFError
    description_tag = models.CharField(max_length=100, default="") 
    game_priority = models.IntegerField(default=0)

    # Conditional Analysis Fields
    free_summary = models.TextField(null=True, blank=True)
    premium_analysis = models.TextField(null=True, blank=True)

    @property
    def net_profit(self):
        """Calculates profit based on 1 unit stake"""
        if not self.is_finished or not self.is_won:
            return -1.00 # Lost stake
        return float(self.odds) - 1

    @property
    def is_won(self):
        if not self.is_finished or self.home_score is None or self.away_score is None:
            return False
        
        # 1X2 Logic
        actual = 'X'
        if self.home_score > self.away_score: 
            actual = '1'
        elif self.away_score > self.home_score: 
            actual = '2'
        
        # Basic check for 1X2. Note: Over/Under/BTTS will need expanded logic here later.
        return self.predicted_outcome == actual

    def clean(self):
        """Enforce Free/Premium logic"""
        if self.is_premium and not self.premium_analysis:
            raise ValidationError({'premium_analysis': "Required for Premium games."})
        if not self.is_premium and not self.free_summary:
            raise ValidationError({'free_summary': "Required for Free games."})

    def __str__(self):
        return self.title

class Payment(models.Model):
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    external_reference = models.CharField(max_length=100, unique=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default="PENDING") # SUCCESS, FAILED, PENDING
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone_number} - {self.status}"
