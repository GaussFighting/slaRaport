import requests
import base64
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta, timezone


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

# TEST ZWRACAMY TYLKO PIERWSZA STRONĘ 
        # Sprawdź, czy jest więcej stron
        # if 'next_page' not in data or data['next_page'] is None:  # Brak więcej danych
        #     break
        # page += 1  # Przejdź do następnej strony        
# TEST KONIEC ODKOMENTOWAĆ PO NAPISANIU FUNKCJI LICZACEJ SLA

# SKASOWAĆ PO TEST
        if 'next_page' not in data or data['next_page']:  # Brak więcej danych
                break
        # page += 1  # Przejdź do następnej strony
# SKASOWAC PO TEST poniżej też tylko 2 elementy z dict

    return tickets[:2]  # Zwróć tylko listę numerów ticketów

# Główna logika
updated_since = '2024-07-01T00:00:00Z'
updated_before = '2024-09-30T23:59:59Z'
updated_ticket_ids = get_tickets_with_updates(updated_since, updated_before)

# Zwróć listę numerów ticketów
print(updated_ticket_ids)
# print(f"Found {len(updated_ticket_ids)} tickets that were updated between July and September 2024:")


# Funkcja pobierania listy auditów dla każdego ticketu
def fetch_ticket_audits(ticket_id):
    print(ticket_id)
    response = requests.get(f"{BASE_URL}/tickets/{ticket_id}/audits.json",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching tickets")
        print(f"Response: {response.json()}")        
    data = response.json()
    return data

# Funkcja pobierania polityki SLA i jej trwania zależnie od czasu nazwa_polityki/pierwsza lub nastepna odpowiedz/priorytet -> 24 opcje
def fetch_sla_policies():
    response = requests.get(f"{BASE_URL}/slas/policies",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching tickets")
        print(f"Response: {response.json()}")        
    data = response.json()

    filtered_policies = [{"title": policy["title"], "policy_metrics": policy["policy_metrics"]} for policy in data['sla_policies']]

    return filtered_policies

sla_policies = fetch_sla_policies()
# print("SLA:", sla_policies)

#funkcja zwraca czas trwania SLA w sekundach, zależnie od parametrów

def sla_duration(policy_name, priority, metric):
    for policy in sla_policies:
        if policy["title"] == policy_name:
            for metrics in policy["policy_metrics"]:
                if (metrics["priority"] == priority) and metrics["metric"] == metric: 
                    return metrics["target_in_seconds"]

# print(sla_duration("SLA ogólne", "low", "first_reply_time"))
# print(sla_duration("SLA ogólne", "normal", "first_reply_time"))
# print(sla_duration("SLA ogólne", "high", "first_reply_time"))
# print(sla_duration("SLA ogólne", "urgent", "first_reply_time"))

# print(sla_duration("SLA ogólne", "low", "next_reply_time"))
# print(sla_duration("SLA ogólne", "normal", "next_reply_time"))
# print(sla_duration("SLA ogólne", "high", "next_reply_time"))
# print(sla_duration("SLA ogólne", "urgent", "next_reply_time"))

# print(sla_duration("SLA nowe", "low", "first_reply_time"))
# print(sla_duration("SLA nowe", "normal", "first_reply_time"))
# print(sla_duration("SLA nowe", "high", "first_reply_time"))
# print(sla_duration("SLA nowe", "urgent", "first_reply_time"))

# print(sla_duration("SLA nowe", "low", "next_reply_time"))
# print(sla_duration("SLA nowe", "normal", "next_reply_time"))
# print(sla_duration("SLA nowe", "high", "next_reply_time"))
# print(sla_duration("SLA nowe", "urgent", "next_reply_time"))

# Funkcja pobierania nazwy i id grupy
def fetch_groups(): 
    response = requests.get(f"{BASE_URL}/groups.json",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching tickets")
        print(f"Response: {response.json()}")        
    data = response.json()

    filtered_groups = [{'group_name': group['name'], 'group_id': group['id']} for group in data['groups']]
    
    # Zwracamy obiekt o tej samej strukturze
    return filtered_groups

groups_info = fetch_groups()
# print(groups_info)

# Funkcja pobierania info o userze id/nazwy i id grupy oraz nazwy grupy do ktorej nalezy user
def fetch_user_data(id):
    response = requests.get(f"{BASE_URL}/users/{id}.json",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching tickets")
        print(f"Response: {response.json()}")        
    data = response.json()

    user_info = {}
    user_info["id"] = data["user"]["id"]
    user_info["name"] = data["user"]["name"]
    user_info["group_id"] = data["user"]["default_group_id"]

    for group in groups_info: 
        if group["group_id"] == user_info["group_id"]:
            user_info["group_name"] = group["group_name"]
        
    return user_info

# print(fetch_user_data(16180946529180))


# poniżej szkic funkcji -- test
def calculate_sla_overruns(audits):
    # Co muszę mieć:
    # przejść po każdym audicie
    # w każdym audicie namierzyć events array i sprawdzić co się "wydarzyło"
    # jeśli wydarzyło się coś istotnego pobrać datę z created_at "2024-10-02T05:12:14Z
    # przypadki
    # godziny biznesowe uwzględnić https://hft71.zendesk.com/api/v2/business_hours/schedules wtf  https://hft71.zendesk.com/admin/objects-rules/rules/schedules 7-17 codzennie
    # na teraz odpuscic sla dla nieoffice hours (wszędzie jest true)


    # Konfiguracja - czas SLA w minutach
    SLA_TIME_MINUTES = 240  # Pobrać w sekundach z funkcji sla_duration
    user_sla = {}
    for audit in audits['audits']:
        # print("Audit:!!", audits['audits'])
        # print("Audit:!!", audit)
        ticket_id = audit['ticket_id']
        created_at = datetime.fromisoformat(audit['created_at'].replace("Z", "+00:00"))  # Używamy UTC
        print("created_at:", created_at)
        events = audit.get('events', [])

        # Zmienna do przechowywania ostatniego przypisania
        last_assignee = None
        last_assigned_time = created_at

        for event in events:
                print("Event:", event)
                if event['type'] == 'Change':
                    field_name = event['field_name']
                    value = event['value']
                    # Sprawdzamy przypisanie użytkownika
                    if field_name == 'assignee_id':
                        if value:
                            last_assignee = value
                            last_assigned_time = created_at  # Ustawiamy czas przypisania na czas audytu
                # Obliczamy, czy SLA zostało przekroczone
                if last_assignee:
                    # Czas trwania SLA
                    sla_expiration_time = last_assigned_time + timedelta(minutes=SLA_TIME_MINUTES)
                    if datetime.now(timezone.utc) > sla_expiration_time:  # Sprawdzamy, czy SLA zostało przekroczone
                        if last_assignee not in user_sla:
                            user_sla[last_assignee] = timedelta()
                        user_sla[last_assignee] += datetime.now(timezone.utc) - sla_expiration_time
        # Formatowanie wyników
        results = {}
        for user_id, overruns in user_sla.items():
            results[user_id] = overruns.total_seconds() / 60  # Zwracamy w minutach
        print(results)
        return results








# for ticket_id in updated_ticket_ids:
#     ticket_audits = fetch_ticket_audits(ticket_id)
#     overrun_results = calculate_sla_overruns(ticket_audits)
#     print(overrun_results)

