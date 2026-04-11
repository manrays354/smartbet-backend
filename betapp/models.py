from django.db import models

class Game(models.Model):
    title = models.CharField(max_length=200)
    match_date = models.DateField()
    free_summary = models.TextField()
    premium_analysis = models.TextField()
    is_premium = models.BooleanField(default=False)
    price = models.IntegerField(default=200)
    # home_score = models.IntegerField(null=True, blank=True)
    # away_score = models.IntegerField(null=True, blank=True)
    # is_finished = models.BooleanField(default=False)

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
