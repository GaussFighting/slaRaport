import requests
import base64
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import pytz
import math


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


# Array z wartościami z intervals skasować jeśli nie jest potrzebne
# bussines_hours_array = []
# for bussines_hours in intervals:
#     bussines_hours_array.append(bussines_hours['start_time'])
#     bussines_hours_array.append(bussines_hours['end_time'])

# print("bussines_hours_array:", bussines_hours_array)
# # Funkcja konwertująca ISO 8601 na datetime
# def iso_to_datetime(iso_string):
#     # Przekształcamy string ISO 8601 na obiekt datetime
#     return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))

# Funkcja czasu Zendesk liczy interval od północy w sobotę między <0 a 10080> ale daty są w ISO

def find_first_saturday_before(date):
    # saturday 23:59 is a time 0 oraz time 10080 in Zendesk
    date = date.astimezone(pytz.timezone("Europe/Warsaw"))
    print("date:", date)
    
    if date.weekday() == 5: #case when date is saturday, and we want earlier saturday
        date -= timedelta(days=1)

    while date.weekday() != 5: 
        date -= timedelta(days=1)

    saturday = datetime(date.year, date.month, date.day, 23, 59, 0)
    saturday = pytz.timezone("Europe/Warsaw").localize(saturday)
    # return first saturday 23:59 before date
    return saturday

def dt_in_bh(start_str, end_str, intervals):
    #start_str and end_str in Zendesk API are in CET +0
    tz = pytz.timezone('Europe/Warsaw')
    start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).astimezone(tz)
    end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).astimezone(tz)
    # dodać warunek konieczny!
    if end_date > start_date: 
        print("start_date:", start_date, "end_date:", end_date, end_date > start_date)
        first_saturday_before_start = find_first_saturday_before(start_date)
        print("first_saturday_before_start:", first_saturday_before_start)
        # switch all dates to unix
        start_unix = int(start_date.timestamp())
        end_unix = int(end_date.timestamp())
        first_saturday_unix = int(first_saturday_before_start.timestamp())
        print("start_unix:", start_unix, "end_unix:", end_unix, "first_saturday_unix:", first_saturday_unix)
        # calc start and end date in minutes
        start_diff = math.floor((start_unix - first_saturday_unix)/60)
        end_diff = math.floor((end_unix - first_saturday_unix)/60)
        print("start_diff:",start_diff,"end_diff:", end_diff)    
        number_of_weeks = math.ceil((end_diff-start_diff)/10080)
        print("number of weeks:", number_of_weeks)
        midnight_days = [2880,4320,5760,7200,8640] #pn-pt
        start_temp = start_diff
        end_temp = end_diff
        sla = 0

        for x in range(number_of_weeks):
            print("ASFDF", x, number_of_weeks)
            for idx, interval in enumerate(intervals):
                if start_temp > interval['end_time']: #check if start is in this day
                    pass
                if idx == (len(intervals) - 1) and start_temp > interval['end_time']: #check if start is in weekend
                    start_temp -= 10080
                    
                else: 
                    print("I:", start_temp, midnight_days[idx], "II", interval['start_time'], interval['end_time'])
                    start = max(start_temp,interval['start_time'])
                    end = min(midnight_days[idx],interval['end_time'])
                    if end > start:
                        sla += end - start
                    print("start:", start, "end:", end, "sla:", sla)
            if x == number_of_weeks-1:
                end_temp -= 10080*number_of_weeks
                print("END_TEMP:", end_temp)
                for idx, interval in enumerate(intervals):
                    if start_temp > interval['end_time']: #check if start is in this day
                        pass
                    if idx == (len(intervals) - 1) and start_temp > interval['end_time']: #check if start is in weekend
                        start_temp -= 10080
                    else:
                        print("I:", start_temp, midnight_days[idx], "II", interval['start_time'], interval['end_time'])
                        start = max(midnight_days[idx] -1440,interval['start_time'])
                        end = min(end_temp,interval['end_time'])
                        if end > start:
                            sla += end - start
                        print("start:", start, "end:", end, "sla:", sla)
            print("final:", sla)
    return sla

# start_str = "2024-08-31T21:59:59Z" 
# end_str = "2024-09-17T14:56:25Z"
# 7198

# start_str = "2024-08-16T21:59:59Z" 
# end_str = "2024-09-17T14:56:25Z"
# 13197

start_str = "2024-09-16T21:59:59Z" 
end_str = "2024-09-17T14:56:25Z"


print(dt_in_bh(start_str,end_str,intervals))

############################ funkcja z srody
# def delta_time_in_bussines_hours_1(start_str, end_str,intervals):
#     # Parse the dates with timezone Europe/Warsaw
    

#     tz = pytz.timezone('Europe/Warsaw')
#     start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).astimezone(tz)
#     end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).astimezone(tz)
#     print("start_date:", start_date, "end_date:", end_date)

#     def find_first_saturday_before(date):
#         # Znalezienie 23:59 pierwszej soboty przed podaną datą
#         # Tworzymy datetime w strefie czasowej Europe/Warsaw
#         date = date.astimezone(pytz.timezone("Europe/Warsaw"))
#         print("date:", date)
        
#         # Znajdujemy dzień tygodnia (sobota to 5 w Pythonie)
#         while date.weekday() != 5:  # Sobota to 5, zaczynając od poniedziałku (0)
#             date -= timedelta(days=1)

#         saturday = datetime(date.year, date.month, date.day, 23, 59, 0)
#         saturday = pytz.timezone("Europe/Warsaw").localize(saturday)
#         # Zwracamy 23:59 tego dnia
#         return saturday

#     print("find_first_saturday_before:", find_first_saturday_before(start_date))
#     # Znajdź pierwszą sobotę przed start_date
#     first_saturday = find_first_saturday_before(start_date)
#     print("first_saturday:", first_saturday)

#     # Przelicz wszystkie daty na unix time
#     start_unix = int(start_date.timestamp())
#     end_unix = int(end_date.timestamp())
#     first_saturday_unix = int(first_saturday.timestamp())
#     print("start_unix:", start_unix, "end_unix:", end_unix, "first_saturday_unix:", first_saturday_unix)
    
#     # Oblicz różnicę między start a sobotą oraz end a sobotą w minutach
#     start_diff = math.floor((start_unix - first_saturday_unix)/60)
#     end_diff = math.floor((end_unix - first_saturday_unix)/60)

#     print("start_diff:",start_diff,"end_diff:", end_diff)
    
#     sla_time = 0  
#     current_start_diff = start_diff  # zmienna pomocnicza
#     current_end_diff = end_diff  # zmienna pomocnicza

    
#     while current_end_diff > 0:
#         print(f"sla_time: {sla_time}, current_end_diff: {current_end_diff}, end_diff: {end_diff}, current_start_diff: {current_start_diff}, start_diff {start_diff}")
#         # Flaga do sprawdzania, czy skończono iteracje po przedziałach
#         found_interval = False  
        
#         for idx, interval in enumerate(intervals): #enumerate to get acces to idx
#             start_time = interval['start_time']
#             end_time = interval['end_time']

#             # Checking if current_start_diff is in interval
#             if start_time <= current_start_diff < end_time and current_start_diff < current_end_diff - 600:
#                 sla_time += end_time - current_start_diff  # add SLA
#                 found_interval = True  

#                 # Check if there is next interval
#                 if idx + 1 < len(intervals):
#                     current_start_diff = intervals[idx + 1]['start_time']  # Set current_start_diff at start_time in next invterval
#                 else:
#                     # Reset week
#                     current_start_diff = intervals[0]['start_time'] #first bussines hour in week
#                     current_end_diff -= 10080  # number of minutes in week
#                 break  

#             # case when end_time is after working hours
#             if idx + 1 < len(intervals):
#                 next_start_time = intervals[idx + 1]['start_time']
#                 if current_end_diff > end_time and current_end_diff < next_start_time:
#                     sla_time += current_end_diff - end_time  # add difference
#                     print(f"current_end_diff is after working hours: {current_end_diff - end_time} to SLA.")
#                     break  

#             # Jeśli jesteśmy na ostatnim przedziale i current_end_diff jest większy od end_time
#             if idx == len(intervals) - 1 and current_end_diff > end_time:
#                 sla_time += current_end_diff - end_time  # Dodaj różnicę do SLA
#                 print(f"Last interval, adding: {current_end_diff - end_time} to SLA.")
#                 break  

#         #no interval, brake
#         if not found_interval:
#             break

#     # # Ustaw start_diff na 1860, jeśli ostatni przedział osiągnięty
#     # if current_end_diff <= 0:
#     #     current_start_diff = 1860

#     # Wyświetlenie całkowitego SLA
#     print("Total SLA Time:", sla_time)
        

# start_str = "2024-09-04T14:57:25Z"
# end_str = "2024-09-17T14:56:25Z"

# sla_result = delta_time_in_bussines_hours_1(start_str, end_str, intervals)

# print(f"sla_result: {sla_result} minutes")

################################################################################
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

