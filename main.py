import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv() # ładowanie zmiennych środowiskowych z pliku .env

# Dane uwierzytelniające Zendesk API
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
API_TOKEN = os.getenv("API_TOKEN")
EMAIL = os.getenv("EMAIL")

# Zakodowanie danych uwierzytelniających
credentials = f"{EMAIL}:{API_TOKEN}".encode('utf-8')
encoded_credentials = base64.b64encode(credentials).decode('utf-8')

# URL bazowy do API
BASE_URL = f'https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2'

# Funkcja do pobrania ticketów z aktualizacjami w danym przedziale czasowym
def get_tickets_with_updates(updated_since, updated_before):
    tickets = []
    page = 1  # Rozpocznij od pierwszej strony
    while True:
        response = requests.get(f"{BASE_URL}/tickets.json?updated_since={updated_since}&updated_before={updated_before}&page={page}",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
        
        if response.status_code != 200:
            print("Error fetching tickets")
            print(f"Response: {response.json()}")
            break
        
        data = response.json()
        for ticket in data['tickets']:
            # Sprawdź, czy 'updated_at' mieści się w przedziale
            # bo api zwraca też stare tickety podpięte pod nowe tickety jako cytat np. 6591 jest podpięty pod 37734 (który dostał tylko autoclose w czerwcu)
            updated_at = ticket['updated_at']
            if updated_since <= updated_at <= updated_before:
                tickets.append(ticket['id'])  # Dodaj ID ticketa

        # Sprawdź, czy jest więcej stron
        if 'next_page' not in data or data['next_page'] is None:  # Brak więcej danych
            break
        page += 1  # Przejdź do następnej strony

    return tickets  # Zwróć tylko listę numerów ticketów

# Główna logika
updated_since = '2024-07-01T00:00:00Z'
updated_before = '2024-09-30T23:59:59Z'
updated_ticket_ids = get_tickets_with_updates(updated_since, updated_before)

# Zwróć listę numerów ticketów
print(updated_ticket_ids)
print(f"Found {len(updated_ticket_ids)} tickets that were updated between July and September 2024:")
