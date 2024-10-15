import requests
import base64
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import pytz


# 1. notes EN only - no exceptions :D EN is one lang you may use :D
# 2. Check if you really need encoded/decoded credentials - looks you use only simple string there (?)
# 3. BASE_URL may be stand alone env variable - no need to mix it with a http string :D <- common way
# 4. is it a valid statement?? if updated_since <= updated_at <= updated_before (?)
# 5. Trello: EN only :) 
# 6. Trello: use at least infinitives in card titles, i.e. NO "kind of returned values", but "normalise a kind returned values" -> a noun doesn't give you an info ;)
# 7. Epic: Overview plan for the application - which languages used, how the data are passed (pros and cons of various ways), do we focus on one-feature app or will we prepare a base for multi-featured app?, how the code will be updated?
# 8 install aplication OnePass for keeping secrets 

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
########################################################################################################################
def fetch_schedules(): 
    response = requests.get(f"{BASE_URL}/business_hours/schedules",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching tickets")
        print(f"Response: {response.json()}")        
    schedules = response.json()
    return schedules['schedules'][0]['intervals']

intervals = fetch_schedules()
print("intervals:", intervals)


# Array z wartościami z intervals
bussines_hours_array = []
for bussines_hours in intervals:
    bussines_hours_array.append(bussines_hours['start_time'])
    bussines_hours_array.append(bussines_hours['end_time'])

print("bussines_hours_array:", bussines_hours_array)
# Funkcja konwertująca ISO 8601 na datetime
def iso_to_datetime(iso_string):
    # Przekształcamy string ISO 8601 na obiekt datetime
    return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))

# Funkcja czasu Zendesk liczy interval od północy w sobotę między <0 a 10080> ale daty są w ISO
def delta_time_in_bussines_hours():
    #obliczanie pełnych dni 
    start_date = "2024-09-04T14:57:25Z"
    end_date = "2024-09-17T17:04:25Z"
    iso_start_date = iso_to_datetime(start_date)
    iso_end_date = iso_to_datetime(end_date)

    tz = pytz.timezone('Europe/Warsaw')
    lolcal_iso_start_date = iso_start_date.astimezone(tz)
    lolcal_iso_end_date = iso_end_date.astimezone(tz)

    print("lolcal_iso_start_date:", lolcal_iso_start_date)
    print("lolcal_iso_end_date:", lolcal_iso_end_date)

    delta_minutes_in_bussines_hours = 0
    full_weekdays_count = -1

    while iso_start_date <= iso_end_date:
        if iso_start_date.weekday() < 5:  # Monday is 0 and Friday is 4
            full_weekdays_count += 1
        iso_start_date += timedelta(days=1)
    
    print("full_weekdays_count:", full_weekdays_count)
    # obliczanie minut po uwzględnieniu pełnych dni
    def minutes_from_saturday_midnight(date):
        # Ustalamy punkt odniesienia (sobota 23:59)
        saturday_midnight = date - timedelta(days=date.weekday() + 1, 
                                                hours=date.hour, 
                                                minutes=date.minute, 
                                                seconds=date.second, 
                                                microseconds=date.microsecond)
        saturday_midnight = saturday_midnight.replace(hour=23, minute=59, second=0, microsecond=0)

        # Obliczamy różnicę minutową między datą a sobotą 23:59
        delta = date - saturday_midnight
        total_minutes = delta.total_seconds() // 60  # Konwersja na minuty
        return int(total_minutes)

    zendesk_start_time = minutes_from_saturday_midnight(lolcal_iso_start_date)
    zendesk_end_time = minutes_from_saturday_midnight(lolcal_iso_end_date)

    def start_time_in_bussines_hours(time):
    
        if time > bussines_hours_array[-1]:
            return bussines_hours_array[0]  # 1860

        if time < 1860:
            return bussines_hours_array[0]  # 1860
    
        for i in range(len(bussines_hours_array) - 1):
            if bussines_hours_array[i] <= time <= bussines_hours_array[i + 1]:
                if i % 2 == 0: #parzyste i to "start" okna z bussines hours
                    return time
                #nieparzyste i oznacza, że jesteśmy po godzinach pracy
                else:
                    return bussines_hours_array[i + 1]
        
        return time  # Zwracamy zendesk_start_time w pozostałych przypadkach
    
    zendesk_start_time_in_bussines_hours = start_time_in_bussines_hours(zendesk_start_time)
    
    def updated_zendesk_end_time(time, start_time):
        end_time = 0
        for i in range(0,len(bussines_hours_array) - 1):
            print("bussines_hours_array[i+2]:", bussines_hours_array[i+2])
            if bussines_hours_array[i] <=  time <= bussines_hours_array[i + 2]:
                end_time = time - bussines_hours_array[i]
                print("end_time:", end_time)
                return start_time + end_time

    zendesk_end_time_in_bussines_hours = updated_zendesk_end_time(zendesk_end_time, zendesk_start_time_in_bussines_hours)

    print("zendesk_start_time:", zendesk_start_time, "zendesk_start_time_in_bussines_hours:", zendesk_start_time_in_bussines_hours, "zendesk_end_time:", zendesk_end_time, "zendesk_end_time_in_bussines_hours:", zendesk_end_time_in_bussines_hours)
    # zwracany czas w minutach
    delta_minutes_in_bussines_hours = full_weekdays_count*60*10

    return delta_minutes_in_bussines_hours + zendesk_end_time_in_bussines_hours - zendesk_start_time_in_bussines_hours

print("Results:", delta_time_in_bussines_hours())









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
        # print("created_at:", created_at)
        events = audit.get('events', [])

        # Zmienna do przechowywania ostatniego przypisania
        last_assignee = None
        last_assigned_time = created_at

        for event in events:
                # print("Event:", event)
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
        # print(results)
        return results








# for ticket_id in updated_ticket_ids:
#     ticket_audits = fetch_ticket_audits(ticket_id)
#     overrun_results = calculate_sla_overruns(ticket_audits)
#     print(overrun_results)

