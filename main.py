import requests
import base64
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import pytz
import math

load_dotenv() # loading env. from file

# Zendesk API Credentials
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
API_TOKEN = os.getenv("API_TOKEN")
EMAIL = os.getenv("EMAIL")

# Coding credentials to string base64
credentials = f"{EMAIL}:{API_TOKEN}".encode('utf-8')
encoded_credentials = base64.b64encode(credentials).decode('utf-8')

# URL base for api
BASE_URL = f'https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2'

# funkction fetchting updated tickets between dates
def get_tickets_with_updates(updated_since, updated_before):
    tickets = []
    page = 1  # start from page 1
    while True:
        response = requests.get(f"{BASE_URL}/tickets.json?updated_since={updated_since}&updated_before={updated_before}&page={page}",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
        
        if response.status_code != 200:
            print("Error fetching tickets")
            print(f"Response: {response.json()}")
            break
        
        data = response.json()
        for ticket in data['tickets']:
            # Check if 'updated_at' is in interval, api return also older tickets witch are added as "history" in case of new order similar to exsiting one in the past for example 6591 is pined to 37734 
            updated_at = ticket['updated_at']
            if updated_since <= updated_at <= updated_before:
                tickets.append(ticket['id'])  # Dodaj ID ticketa

# TEST ZWRACAMY TYLKO PIERWSZA STRONĘ 
        # Check if there is more pages
        # if 'next_page' not in data or data['next_page'] is None:  
        #     break
        # page += 1       
# TEST KONIEC ODKOMENTOWAĆ PO NAPISANIU FUNKCJI LICZACEJ SLA

# SKASOWAĆ PO TEST
        if 'next_page' not in data or data['next_page']:  
                break
        # page += 1  
# SKASOWAC PO TEST poniżej też tylko 2 elementy z dict

    return tickets[:1]  # return array of tickets id

# Main logic
updated_since = '2024-07-01T00:00:00Z'
updated_before = '2024-09-30T23:59:59Z'
updated_ticket_ids = get_tickets_with_updates(updated_since, updated_before)

print("returned tickets id:", updated_ticket_ids)

# Function fetching audits of any ticket by id
def fetch_ticket_audits(ticket_id):
    response = requests.get(f"{BASE_URL}/tickets/{ticket_id}/audits.json",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching tickets")
        print(f"Response: {response.json()}")        
    data = response.json()
    return data

# Funcion fetching SLA policy and duration of policy according to policy name, and policy metrics (priority) -> 24 options
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
print("SLA:", sla_policies)

# Function returns sla_duration in seconds according to metrics, title and priority

def sla_duration(policy_name, priority, metric):
    for policy in sla_policies:
        if policy["title"] == policy_name:
            for metrics in policy["policy_metrics"]:
                if (metrics["priority"] == priority) and metrics["metric"] == metric: 
                    return metrics["target_in_seconds"]

# Function fetch group id and group name
def fetch_groups(): 
    response = requests.get(f"{BASE_URL}/groups.json",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching tickets")
        print(f"Response: {response.json()}")        
    data = response.json()

    filtered_groups = [{'group_name': group['name'], 'group_id': group['id']} for group in data['groups']]
    
    return filtered_groups

groups_info = fetch_groups()
# print(groups_info)

# Function fetch user info and add group name after user id in user info (just for future needs)
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

# Function fetch schedules of bussines hours
def fetch_schedules(): 
    response = requests.get(f"{BASE_URL}/business_hours/schedules",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching tickets")
        print(f"Response: {response.json()}")        
    schedules = response.json()
    return schedules['schedules'][0]['intervals']

intervals = fetch_schedules()

# Zendesk count time since 23:59 at Saturday as a 0 or 10080, but dates in audits are in string

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
    print("STARTDATEEEE:", start_str)
    start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).astimezone(tz)
    end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).astimezone(tz)
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
    amount_of_days = math.ceil(end_diff/1440) #number of steps and last step for end_date
    start_step = math.floor(start_diff/1440) #step with start_date

    print("start_diff:",start_diff,"end_diff:", end_diff, "amount_of_days:",amount_of_days, "start_step:", start_step)   
    day_min_arr = [{'start_day': 1, 'end_day': 1440},{'start_day': 1441, 'end_day': 2880},{'start_day': 2881, 'end_day': 4320},{'start_day': 4321, 'end_day': 5760},{'start_day': 5761, 'end_day': 7200},{'start_day': 7201, 'end_day': 8640},{'start_day': 8641, 'end_day': 10080},]
   
   #neasted function is needed here!
    def bussines_hours_in_whole_week(day_min_arr, intervals):
        bh_day_min_arr = []

        # Iterate over each day interval
        for day in day_min_arr:
            day_start = day['start_day']
            day_end = day['end_day']
            overlap_found = False  # Flag to track if any overlap is found

            # Iterate over each interval to check overlap
            for interval in intervals:
                interval_start = interval['start_time']
                interval_end = interval['end_time']

                # Check for overlap between day and interval
                overlap_start = max(day_start, interval_start)
                overlap_end = min(day_end, interval_end)

                # If they overlap, add the overlapping range to the result
                if overlap_start <= overlap_end:
                    bh_day_min_arr.append({'start_time': overlap_start, 'end_time': overlap_end})
                    overlap_found = True  # Set flag when overlap is found
                    break  # Exit loop once we find the first overlap

            # If no overlap was found, append a zeroed-out object
            if not overlap_found:
                bh_day_min_arr.append({'start_time': 0, 'end_time': 0})

        return bh_day_min_arr

    bh_day_min_arr = bussines_hours_in_whole_week(day_min_arr,intervals)
    print("bh_day_min_arr:", bh_day_min_arr)
    
    sla = 0
    start_date_temp = start_diff
    end_date_temp = end_diff
    for i in range(0,amount_of_days):
        if i > 0 and i%7==0:
            start_date_temp -= 10080
            end_date_temp -= 10080
            # print(i,"start_date_temp:",start_date_temp,"end_date_temp",end_date_temp)
        if i < start_step : 
            # print(i,"empty step")
            pass
        if i == start_step and start_step < amount_of_days - 1: 
            print(i,"add first sla and go on")
            # print(start_date_temp,day_min_arr[i%7]['end_day'],bh_day_min_arr[i%7]['start_time'],bh_day_min_arr[i%7]['end_time'])
            start = max(start_date_temp,bh_day_min_arr[i%7]['start_time'])
            end = min(day_min_arr[i%7]['end_day'],bh_day_min_arr[i%7]['end_time'])     
            # print("start:", start, "end:", end)
            if end > start:
                sla += end - start
                # print("start:", start, "end:", end, "sla:", sla)
        if i == start_step and start_step == amount_of_days - 1:
            print(i,"sla starts and ends in the same day")
            # print(start_date_temp,end_date_temp, bh_day_min_arr[i%7]['start_time'],bh_day_min_arr[i%7]['end_time'])
            start = max(start_date_temp,bh_day_min_arr[i%7]['start_time'])
            end = min(end_date_temp, bh_day_min_arr[i%7]['end_time'])     
            # print("start:", start, "end:", end)
            if end > start:
                sla += end - start
                # print("start:", start, "end:", end, "sla:", sla)
        if start_step < i < amount_of_days - 1:
            print(i,"add full day to sla")
            # print(day_min_arr[i%7]['start_day'],day_min_arr[i%7]['end_day'],bh_day_min_arr[i%7]['start_time'],bh_day_min_arr[i%7]['end_time'])
            start = max(day_min_arr[i%7]['start_day'],bh_day_min_arr[i%7]['start_time'])
            end = min(day_min_arr[i%7]['end_day'],bh_day_min_arr[i%7]['end_time'])     
            # print("start:", start, "end:", end)
            if end > start:
                sla += end - start
                # print("start:", start, "end:", end, "sla:", sla)
        if start_step < i and i == amount_of_days -1:
            print(i,"add last day to sla")
            # print(day_min_arr[i%7]['start_day'],end_date_temp, bh_day_min_arr[i%7]['start_time'],bh_day_min_arr[i%7]['end_time'])
            start = max(day_min_arr[i%7]['start_day'],bh_day_min_arr[i%7]['start_time'])
            end = min(end_date_temp, bh_day_min_arr[i%7]['end_time'])     
            # print("start:", start, "end:", end)
            if end > start:
                sla += end - start
                # print("start:", start, "end:", end, "sla:", sla)
    if end_date < start_date: 
        print("Error, start_date cannot be greater then end_date")
    return sla

# start_str = "2024-09-17T21:59:59Z" # saturday one minute before midnight, first iteration is empty! 
# end_str = "2024-09-17T8:59:25Z"
# error :D

# start_str = "2024-08-16T21:59:59Z" 
# end_str = "2024-09-17T14:56:25Z"
# 13197

# start_str = "2024-09-16T21:59:59Z" 
# end_str = "2024-09-17T14:56:25Z" 
# 597

start_str = "2024-08-31T21:59:59Z" 
end_str = "2024-09-02T5:03:25Z" 
# 597

print("dt_in_bh:", dt_in_bh(start_str,end_str,intervals))


################################################################################
def calculate_breached_sla(audits):
    results = {}
    users_sla = []
    user = {}
    last_assigned_user = None
    last_assigned_group = None
    temp_sla_is_breached_after = ""
    temp_sla_start_date = ""
    temp_sla_end_date = ""
    for idx, audit in enumerate(audits['audits']):
        print(f"{idx} XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        for index,event in enumerate(audit['events']):
            # print(idx, index, event, "\n")
            print(idx, index, "\n", "temp_sla_start_date:", temp_sla_start_date)
            if 'via' in event and event['via']['source']['rel'] == 'sla_target_change' and event['value'] is not None: # When event['value'] is null -> then canceled policy
                temp_sla_is_breached_after = event['value']['minutes'] #add index to it? :>
                temp_sla_start_date = audit['created_at']
                # print("temp_sla_start_date", temp_sla_start_date, "start counting SLA",temp_sla_is_breached_after)
            if "field_name" in event and event['field_name'] == 'group_id':
                last_assigned_group = event['value']
                # temp_sla_start_date = audit['created_at']
                # print("last_assigned_group", last_assigned_group)
            if "field_name" in event and event['field_name'] == 'assignee_id':
                last_assigned_user = event['value']
                # temp_sla_start_date = audit['created_at']
                # print("last_assigned_user", last_assigned_user)
            # end date conditions! #1 answer to customer #2 answer not required #3 reassigne group or user id
            condition_1 = 'via' in event and event['type'] == 'Notification' and event['via']['source']['from']['title'] == 'Notify requester and CCs of comment update'
            condition_2 = event['type'] == "Change" and event["value"] == "1" and event["field_name"] == "360020814459"
            condition_3 = ("field_name" in event and event['field_name'] == 'group_id' and 'previous_value' in event and last_assigned_group != event["previous_value"]) or ("field_name" in event and event['field_name'] == 'assignee_id' and 'previous_value' in event and last_assigned_user != event["previous_value"])
            if condition_1 or condition_2 or condition_3:
                if condition_1:
                    if temp_sla_start_date: #safety agents send few answers withour customer messages
                        temp_sla_end_date = audit['created_at']
                        print("ASDXFFFF:",temp_sla_start_date)
                        sla = dt_in_bh(temp_sla_start_date,temp_sla_end_date, intervals) - temp_sla_is_breached_after
                        if sla > 0:
                            print("Sla przekroczone, odpowiedź do klienta, Zwróć obiekt do arraya:", "last_assigned_user:", last_assigned_user, "last_assigned_group", last_assigned_group, "SLA:", sla)
                            user['assignee_id'] = last_assigned_user
                            user['group_id'] = last_assigned_group
                            user['sla'] = sla
                            user['sla_start'] = temp_sla_start_date
                            user['sla_end'] = temp_sla_end_date
                            users_sla.append(user.copy())
                            print("users_sla:", users_sla)
                        if sla <= 0:
                            print("Sla nie jest przekroczone")
                        temp_sla_start_date = ""
                    pass
                if condition_2: 
                    temp_sla_start_date = ""
                    temp_sla_is_breached_after = ""
                    print("Odpowiedź niewymagana, kasuje ostatnio liczone SLA, wyjdź z pętli, wyzeruj temp_sla_start_date i temp_sla_is_breached_after > to chyba nie")  
                    pass  
                if condition_3:
                    if 'previous_value' not in event:
                        print("Poprzedni użytkownik/grupa nie był przypisany, więc SLA będziemy liczyli dla tego co dopiero zostanie przypisany - brak zmiany agenta/grupy")
                        pass
                    if event['previous_value']:
                        if temp_sla_start_date:
                            temp_sla_end_date = audit['created_at']
                            sla = dt_in_bh(temp_sla_start_date,temp_sla_end_date, intervals) - temp_sla_is_breached_after
                            (print("Zmiana użytkownika/grupy liczymy SLA", event['value'], event["previous_value"],temp_sla_end_date,temp_sla_start_date, "sla:", sla ))
                            if sla > 0: # 
                                print(audit['created_at'], "Zwróć obiekt do arraya:", "last_assigned_user:", last_assigned_user, "last_assigned_group", last_assigned_group, "SLA:", sla)
                                user['assignee_id'] = event["previous_value"]
                                user['group_id'] = event["previous_value"]
                                user['sla'] = sla
                                user['sla_start'] = temp_sla_start_date
                                user['sla_end'] = temp_sla_end_date
                                users_sla.append(user.copy()) # COPY : O obiekty w pythonie są mutowalnej. jesli referencja tego samego obiektu jest dodawana wielokrotnie do listy to kazda zmiana obiektu powoduje zmiane wczesniejszych kopii
                                print("users_sla:", users_sla, "Dodać warunek na nastepne liczenie, rekurencja?, bo mamy dane startowa i nadal szukamy czegos pomiedzy cond_1-3")
                                # temp_sla_start_date = temp_sla_end_date
                                print("Condition3, zmiana usera w trakcie SLA", last_assigned_user, last_assigned_group, temp_sla_start_date)
                                pass
                            if sla <= 0:
                                print("Sla jest nieprzekroczone")
                            print("Pobierz datę, policz sla do tej grupy/użytkownika z previous_value, nadpisz sla_start-date bo od tego momentu liczymy dla nowego użykownika")
                pass
                print(audit['created_at'])
                print("123")
        # print("BBB", users_sla)
        if users_sla:
            results['users_sla'] = users_sla
            results['ticket_id'] = audits['audits'][0]['ticket_id']
        else:
            print("No breached sla")
    return results

 







# Loop over tickets and make audit for each
# for ticket_id in updated_ticket_ids:
#     ticket_audits = fetch_ticket_audits(ticket_id)
#     breached_results = calculate_breached_sla(ticket_audits)
#     print(breached_results)

ticket_audits = fetch_ticket_audits('41645') # 886 i 5
# ticket_audits = fetch_ticket_audits('41257') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('41265') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('41856') # tu nie było przekroczonych 
# ticket_audits = fetch_ticket_audits('40868') # tu nie było przekroczonych
ticket_audits = fetch_ticket_audits('40085') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('X') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('X') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('X') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('X') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('X') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('X') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('X') # tu nie było przekroczonych


print("AA", ticket_audits)
breached_results = calculate_breached_sla(ticket_audits)
print("breached_results:", breached_results)

# brak warunku na ticket w którym właśnie jest liczone SLA (przekroczone) i nic się więcej nie zadziało!
# brak warunku na krótki ticket w którym nikt nie został przypisany, a sla się liczyło i ktoś odpowiedział  40868
# export do csv? stwórz z niepustych obiektów! [Raport złamanych SLA] Najlepiej w postaci ticket_id / suma sla / assignee_id#1 / group_id#1 / sla#1 i nastepnę /  || Numer ticketu / suma sla / imię i nazwisko#1 / nazwa grupy #1 / przekroczone sla [min]#1
# na koncu podac ile było ticketów z SLA przekroczonym o mniej niz godzine, o mniej niz 2 godziny i o wiecej niz 2h
# zamienić assigne_id na username
# group_id na nazwe grupy
# do zrobienia w przyszłości, można wyrzucić ile każdy user/grupa ile miała złamanych sla i o ile i ile średnio 

