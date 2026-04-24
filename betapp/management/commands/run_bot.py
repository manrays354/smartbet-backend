import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from betapp.models import Game

class Command(BaseCommand):
    def handle(self, *args, **options):
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://tobetornot.com"
        
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find_all('tr')[1:]

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 6: continue
            
            # 1. Parse Info
            match_info = cols[1].get_text(" ", strip=True).replace("home team - away team:", "").strip()
            match_data = re.search(r'(.+?)\s+(\d{4}.*?\d{2}:\d{2})', match_info)
            if not match_data: continue
            
            teams = match_data.group(1).strip()
            date_str = match_data.group(2).replace(", ", " ").strip()

            # 2. Extract Prediction
            raw_tip = cols[3].get_text(strip=True).replace("tip A:", "").strip()
            prediction = {'1': '1', 'X': 'X', '2': '2', '1X': '1', 'X2': '2'}.get(raw_tip, '1')

            # 3. CALCULATE ODDS FROM PERCENTAGES (Fallback Solution)
            # The site lists percentages like "1: 45% X: 30% 2: 25%" in Column 3 (Index 2)
            prob_text = cols[2].get_text(strip=True)
            
            # Find the percentage for our predicted outcome
            # e.g., if prediction is '1', find the number before '%' after '1:'
            prob_match = re.search(rf"{prediction}:\s*(\d+)%", prob_text)
            
            if prob_match:
                percentage = int(prob_match.group(1))
                # Calculate Fair Odds: 100 / percentage (e.g., 100 / 50 = 2.00)
                final_odd = round(100 / percentage, 2) if percentage > 0 else 1.50
            else:
                final_odd = 1.50 # Hard fallback if percentages are missing

            # 4. Save to DB
            dt = self.parse_date(date_str)
            Game.objects.update_or_create(
                title=teams, 
                match_date=timezone.make_aware(dt),
                defaults={
                    'predicted_outcome': prediction,
                    'odds': final_odd,
                    'is_premium': False,
                    'bookmaker': "Statistical",
                    'free_summary': f"AI Prediction based on {prob_text}. Calculated odds: {final_odd}"
                }
            )
            self.stdout.write(f"SYNCED: {teams} | Tip: {prediction} | Prob-based Odds: {final_odd}")

    def parse_date(self, date_str):
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%d-%m %H:%M'):
            try: return datetime.strptime(date_str, fmt)
            except: continue
        return datetime.now()
