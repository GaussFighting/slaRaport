import requests
import base64
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import pytz
import math
import csv
import time

# CR: Pls search over "CR:"
# CR: Pls move the helper functions into utils file :)
# CR: I'd recommend to set up a linter for Python 
# CR: Prints should be written in English as well ;) Love me! :D 

load_dotenv() # loading env. from file

# Zendesk API Credentials
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN") # CR: Looks it might be moved to a separate file, i.e. "credentials.py"
API_TOKEN = os.getenv("API_TOKEN")
EMAIL = os.getenv("EMAIL")

# Coding credentials to string base64
credentials = f"{EMAIL}:{API_TOKEN}".encode('utf-8')
encoded_credentials = base64.b64encode(credentials).decode('utf-8')

# URL base for api
BASE_URL = f'https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2'

# funkction fetchting updated tickets between dates
def get_tickets_with_updates(updated_since, updated_before): #CR: Util function
    tickets = []
    page = 1  # start from page 1
    while True: # CR: Pls avoid using "while" loop, if it might be ommited :) If you know how many pages you may encounter, then "for" loop would be much better :)
        response = requests.get(f"{BASE_URL}/tickets.json?updated_since={updated_since}&updated_before={updated_before}&page={page}",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
        if response.status_code != 200:
            print("Error fetching tickets between dates") # CR: i.e. if something wrong with page 3, but pages 4, 5, 6 are fine, then you will break too early. I'd recommend to use "continue" instead
            print(f"Response: {response.json()}")
            break
        
        data = response.json()
        for ticket in data['tickets']:
            # Check if 'updated_at' is in interval, api return also older tickets witch are added as "history" in case of new order similar to exsiting one in the past for example 6591 is pined to 37734 CR: English improvement needed :)
            updated_at = ticket['updated_at']
            if updated_since <= updated_at <= updated_before:
                tickets.append(ticket['id'])  # Dodaj ID ticketa CR: EN pls :)

        # Check if there is more pages
        if 'next_page' not in data or data['next_page'] is None:  
            break
        page += 1       

    return tickets # return array of tickets id

# Main logic
updated_since = '2024-07-01T00:00:00Z'
updated_before = '2024-09-30T23:59:59Z'
# ODKOMENTOWAC PO TEST CR: EN pls :)
updated_ticket_ids = get_tickets_with_updates(updated_since, updated_before)
number_of_checked_tickets = len(updated_ticket_ids)

print("number_of_checked_tickets:", number_of_checked_tickets)
print("returned tickets id:", updated_ticket_ids)
# ODKOMENTOWAC PO TEST CR: EN pls :)

# Function fetching audits of any ticket by ticket id
def fetch_ticket_audits(ticket_id):  #CR: Util function
    time.sleep(0.3)
    #https://developer.zendesk.com/api-reference/introduction/rate-limits/ Proffessional ma 400/minute CR: EN pls :)
    response = requests.get(f"{BASE_URL}/tickets/{ticket_id}/audits.json",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print(ticket_id) #CR: in such a case throwing an error would be more proper. Just a good and often used habit to throw an err, if you may encounter it
        print("Error fetching tickets audits")
        print(f"Response: {response.json()}")        
    data = response.json()

    return data

# Function fetching SLA policy and duration of policy according to policy name, and policy metrics (priority) -> 24 options 
def fetch_sla_policies():  #CR: Util function
    response = requests.get(f"{BASE_URL}/slas/policies",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching sla policies") #CR: throwing an err would be better here :) 
        print(f"Response: {response.json()}")        
    data = response.json()

    filtered_policies = [{"title": policy["title"], "policy_metrics": policy["policy_metrics"]} for policy in data['sla_policies']]

    return filtered_policies

sla_policies = fetch_sla_policies()
# print("SLA:", sla_policies)

# Function returns sla_duration in seconds according to metrics, title and priority
def sla_duration(policy_name, priority, metric):  #CR: Util function
    for policy in sla_policies:
        if policy["title"] == policy_name:
            for metrics in policy["policy_metrics"]:
                if (metrics["priority"] == priority) and metrics["metric"] == metric: 
                    return metrics["target_in_seconds"]

# Function fetch group id and group name  #CR: English tiny improvement needed here
def fetch_groups():  #CR: Util function
    response = requests.get(f"{BASE_URL}/groups.json",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching groups")
        print(f"Response: {response.json()}")        
    data = response.json()

    filtered_groups = [{'group_name': group['name'], 'group_id': group['id']} for group in data['groups']]
    
    return filtered_groups

groups_info = fetch_groups()

# Function fetch user info and add group name after user id in user info (just for future needs)
def fetch_user_data(id): #CR: Util function
    response = requests.get(f"{BASE_URL}/users/{id}.json",
                                headers={'Authorization': f'Basic {encoded_credentials}'}) #CR: When you have so many different endpoint, maybe you could consider to store them in a separated file i.e. "endpoints" and import a particular constants from it(?)
    if response.status_code != 200:
        print(f"Error fetching user data of {id}") #CR: throwing an err would be better here :) 
        print(f"Response: {response.json()}") 
        user_info = {}
        user_info["id"] = id
        user_info["name"] = "Brak przypisanego użytkownika"
        user_info["group_id"] = "Brak przypisanej grupy" 
        user_info["group_name"] = "Brak przypisanej grupy"
    
    else: #CR: Is "else" condition needed here?
        data = response.json()
        user_info = {}
        user_info["id"] = data["user"]["id"]
        user_info["name"] = data["user"]["name"]
        user_info["group_id"] = data["user"]["default_group_id"]

        for group in groups_info: 
            if not "group_name" in user_info:
                user_info["group_name"] = "Użytkownik nieprzypisany do żadnej grupy"
            if group["group_id"] == user_info["group_id"]:
                user_info["group_name"] = group["group_name"]
            
    return user_info
# print("USER INFO:", fetch_user_data(16180946529180))

# Function fetch schedules of bussines hours
def fetch_schedules(): #CR: Util function
    response = requests.get(f"{BASE_URL}/business_hours/schedules",
                                headers={'Authorization': f'Basic {encoded_credentials}'})
    if response.status_code != 200:
        print("Error fetching schedules")
        print(f"Response: {response.json()}")        
    schedules = response.json()
    return schedules['schedules'][0]['intervals']

intervals = fetch_schedules()
# Zendesk count time since 23:59 at Saturday as a 0 or 10080, but dates in audits are in string

def find_first_saturday_before(date): #CR: Util function
    # saturday 23:59 is a time 0 oraz time 10080 in Zendesk #CR: EN pls :)
    date = date.astimezone(pytz.timezone("Europe/Warsaw"))
    # print("date:", date)
    
    if date.weekday() == 5: #case when date is saturday, and we want earlier saturday #CR: I'd improve an explanation of that logic only ;)
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
    # print("STARTDATEEEE:", start_str)
    start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).astimezone(tz)
    end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC).astimezone(tz)
    first_saturday_before_start = find_first_saturday_before(start_date)
    # print("first_saturday_before_start:", first_saturday_before_start)
    # switch all dates to unix time
    start_unix = int(start_date.timestamp())
    end_unix = int(end_date.timestamp())
    first_saturday_unix = int(first_saturday_before_start.timestamp())
    # print("start_unix:", start_unix, "end_unix:", end_unix, "first_saturday_unix:", first_saturday_unix)
    # calc start and end date in minutes
    start_diff = math.floor((start_unix - first_saturday_unix)/60)
    end_diff = math.floor((end_unix - first_saturday_unix)/60)
    amount_of_days = math.ceil(end_diff/1440) #number of steps and last step for end_date  #CR: Pls leave a comment for Kuba from the future about "1440" :)
    start_step = math.floor(start_diff/1440) #step with start_date

    # print("start_diff:",start_diff,"end_diff:", end_diff, "amount_of_days:",amount_of_days, "start_step:", start_step)   
    day_min_arr = [{'start_day': 1, 'end_day': 1440},{'start_day': 1441, 'end_day': 2880},{'start_day': 2881, 'end_day': 4320},{'start_day': 4321, 'end_day': 5760},{'start_day': 5761, 'end_day': 7200},{'start_day': 7201, 'end_day': 8640},{'start_day': 8641, 'end_day': 10080},]
   
   #neasted function is needed here!
    def bussines_hours_in_whole_week(day_min_arr, intervals):  #CR: Util function
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
    # print("bh_day_min_arr:", bh_day_min_arr)
    
    sla = 0
    start_date_temp = start_diff
    end_date_temp = end_diff
    for i in range(0,amount_of_days):
        if i > 0 and i%7==0:
            start_date_temp -= 10080
            end_date_temp -= 10080
            # print(i,"start_date_temp:",start_date_temp,"end_date_temp",end_date_temp)
        if i < start_step : 
            # print(i,"empty step")  #CR: Maybe "continue" would be better here? Otherwise you still check next if-conditions
            pass
        if i == start_step and start_step < amount_of_days - 1: #CR: Would it be OK if i.e. two IFs were matched and executed? If not, pls end each "if" code block using "continue". And just a question only: is start_step < amount_of_days - 1 condition required?
            # print(i,"add first sla and go on")
            # print(start_date_temp,day_min_arr[i%7]['end_day'],bh_day_min_arr[i%7]['start_time'],bh_day_min_arr[i%7]['end_time'])
            start = max(start_date_temp,bh_day_min_arr[i%7]['start_time']) #CR: Since you use "bh_day_min_arr[i%7]['start_time']", "bh_day_min_arr[i%7]['end_time']", "day_min_arr[i%7]['end_day']" and "day_min_arr[i%7]['start_day']" maybe you could set them above as a shoter-named variables? :)
            end = min(day_min_arr[i%7]['end_day'],bh_day_min_arr[i%7]['end_time'])     
            # print("start:", start, "end:", end)
            if end > start:
                sla += end - start
                # print("start:", start, "end:", end, "sla:", sla)
        if i == start_step and start_step == amount_of_days - 1:
            # print(i,"sla starts and ends in the same day")
            # print(start_date_temp,end_date_temp, bh_day_min_arr[i%7]['start_time'],bh_day_min_arr[i%7]['end_time'])
            start = max(start_date_temp,bh_day_min_arr[i%7]['start_time'])
            end = min(end_date_temp, bh_day_min_arr[i%7]['end_time']) # CR: Basically you repeat the logic of the first IF-block here. It differs only in that line. I'd recommend to make a tiny refactor :)  
            # print("start:", start, "end:", end)
            if end > start:
                sla += end - start
                # print("start:", start, "end:", end, "sla:", sla)
        if start_step < i < amount_of_days - 1:
            # print(i,"add full day to sla")
            # print(day_min_arr[i%7]['start_day'],day_min_arr[i%7]['end_day'],bh_day_min_arr[i%7]['start_time'],bh_day_min_arr[i%7]['end_time'])
            start = max(day_min_arr[i%7]['start_day'],bh_day_min_arr[i%7]['start_time'])
            end = min(day_min_arr[i%7]['end_day'],bh_day_min_arr[i%7]['end_time'])     
            # print("start:", start, "end:", end)
            if end > start:
                sla += end - start
                # print("start:", start, "end:", end, "sla:", sla)
        if start_step < i and i == amount_of_days -1:
            # print(i,"add last day to sla")
            # print(day_min_arr[i%7]['start_day'],end_date_temp, bh_day_min_arr[i%7]['start_time'],bh_day_min_arr[i%7]['end_time'])
            start = max(day_min_arr[i%7]['start_day'],bh_day_min_arr[i%7]['start_time'])
            end = min(end_date_temp, bh_day_min_arr[i%7]['end_time']) # CR: Basically you repeat the logic above here. It differs only in that line. I'd recommend to make a tiny refactor :)
            # print("start:", start, "end:", end)
            if end > start:
                sla += end - start
                # print("start:", start, "end:", end, "sla:", sla)
    if end_date < start_date: 
        print("Error, start_date cannot be greater then end_date") 
    return sla

# print("dt_in_bh:", dt_in_bh(start_str,end_str,intervals))

def calculate_breached_sla(audits, last_assigned_user = None, last_assigned_group = None, results = None, users_sla = None, user = None, sla_is_breached_after = 0, sla_start_date = "", sla_end_date = ""):
    # print(audits[0]['ticket_id'])
    recursion_audits = audits
    temp_last_assigned_user = last_assigned_user
    temp_last_assigned_group = last_assigned_group
    if results is None:
        results = {}
    temp_results = results
    if users_sla is None:
        users_sla = []
    temp_users_sla = users_sla
    if user is None:
        user = {}
    temp_user = user
    temp_sla_is_breached_after = sla_is_breached_after
    temp_sla_start_date = sla_start_date
    temp_sla_end_date = sla_end_date
    is_recursion = False
    for idx, audit in enumerate(audits):
        # print(idx, len(audits))
        # print(f"{idx} XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        if 'events' in audit:
            for event in audit['events']:
                    # print(idx, index, event, "\n")
                # print(idx, index, "\n", "temp_sla_start_date:", temp_sla_start_date)
                if 'via' in event and event['via']['source']['rel'] == 'sla_target_change' and event['value'] is not None: # When event['value'] is null -> then canceled policy
                    temp_sla_is_breached_after = event['value']['minutes'] #add index to it? :>
                    temp_sla_start_date = audit['created_at']
                    # print("temp_sla_start_date", temp_sla_start_date, "start counting SLA",temp_sla_is_breached_after)
                if "field_name" in event and event['field_name'] == 'group_id':
                    temp_last_assigned_group = event['value']
                    # temp_sla_start_date = audit['created_at']
                    # print("temp_last_assigned_group", temp_last_assigned_group)
                if "field_name" in event and event['field_name'] == 'assignee_id':
                    temp_last_assigned_user = event['value']
                    # temp_sla_start_date = audit['created_at']
                    # print("temp_last_assigned_user", temp_last_assigned_user)
                # end date conditions! #1 answer to customer #2 answer not required #3 reassigne group or temp_user id
                condition_1 = 'via' in event and event['type'] == 'Notification' and event['via']['source']['from']['title'] == 'Notify requester and CCs of comment update'
                condition_2 = event['type'] == "Change" and event["value"] == "1" and event["field_name"] == "360020814459"
                condition_3 = ("field_name" in event and event['field_name'] == 'group_id' and 'previous_value' in event and temp_last_assigned_group != event["previous_value"]) or ("field_name" in event and event['field_name'] == 'assignee_id' and 'previous_value' in event and temp_last_assigned_user != event["previous_value"])
                if condition_1 or condition_2 or condition_3: # CR: Do we need that statement here, since we check particular condition (1, 2, 3) separately below?
                    if condition_1:
                        if temp_sla_start_date: #safety agents send few answers withour customer messages
                            temp_sla_end_date = audit['created_at']
                            # print("ASDXFFFF:",temp_sla_start_date)
                            sla = dt_in_bh(temp_sla_start_date,temp_sla_end_date, intervals) - temp_sla_is_breached_after
                            if sla > 0:
                                # print("Sla przekroczone, odpowiedź do klienta, Zwróć obiekt do arraya:", "temp_last_assigned_user:", temp_last_assigned_user, "temp_last_assigned_group", temp_last_assigned_group, "SLA:", sla)
                                temp_user['assignee_id'] = temp_last_assigned_user
                                temp_user['name'] = fetch_user_data(temp_user['assignee_id'])['name']
                                # temp_user['group_name'] = fetch_user_data(temp_user['assignee_id'])['group_name']
                                temp_user['group_id'] = temp_last_assigned_group
                                for group in groups_info:
                                    if temp_last_assigned_group is not None and int(group["group_id"]) == int(temp_last_assigned_group):
                                        temp_user['group_name'] = group['group_name']
                                    else: 
                                        temp_user['group_name'] = "Brak przypisanej grupy"
                                temp_user['sla'] = sla
                                temp_user['sla_start'] = temp_sla_start_date
                                temp_user['sla_end'] = temp_sla_end_date
                                temp_users_sla.append(temp_user.copy())
                                # print("temp_users_sla:", temp_users_sla)
                            if sla <= 0: # CR: If we don't do anything with that condition, is it needed? Maybe a comment would be enough? Or commented together with "print" line?
                                # print("Sla nie jest przekroczone")
                                pass
                            temp_sla_start_date = ""
                        pass # CR: Shouldn't we consider using a "continue" instead of "pass"? There is always a risk that two or more IF conditions could be fulfiled
                    if condition_2: 
                        temp_sla_start_date = ""
                        temp_sla_is_breached_after = ""
                        # print("Odpowiedź niewymagana, kasuje ostatnio liczone SLA, wyjdź z pętli, wyzeruj temp_sla_start_date i temp_sla_is_breached_after > to chyba nie")  
                        pass  
                    # print("index przed condition 3", idx)
                    if condition_3:
                        if 'previous_value' not in event:
                            # print("Poprzedni użytkownik/grupa nie był przypisany, więc SLA będziemy liczyli dla tego co dopiero zostanie przypisany - brak zmiany agenta/grupy")
                            pass
                        if event['previous_value']: # CR: Couldn't we merge that IF condition with a one above? At least we may leave just a comment about "'previous_value' not in event" case only
                            if temp_sla_start_date:
                                temp_sla_end_date = audit['created_at']
                                sla = dt_in_bh(temp_sla_start_date,temp_sla_end_date, intervals) - temp_sla_is_breached_after
                                # (print("Zmiana użytkownika/grupy liczymy SLA", event['value'], event["previous_value"],temp_sla_end_date,temp_sla_start_date, "sla:", sla, "ticket:", audit['ticket_id'] ))
                                if sla > 0: # 
                                    is_recursion = True
                                    # print("A", idx, len(audits))
                                    # print(audit['created_at'], "Zwróć obiekt do arraya:", "temp_last_assigned_user:", temp_last_assigned_user, "temp_last_assigned_group", temp_last_assigned_group, "SLA:", sla)
                                    temp_user['assignee_id'] = event["previous_value"]
                                    temp_user['name'] = fetch_user_data(temp_user['assignee_id'])['name']
                                    temp_user['group_id'] = temp_last_assigned_group
                                    # print("temp_last_assigned_group", temp_last_assigned_group)
                                    # print("KeyError", temp_user['assignee_id'], audit['ticket_id'])
                                    # temp_user['group_name'] = fetch_user_data(temp_user['assignee_id'])['group_name']
                                    for group in groups_info:
                                        if temp_user['group_id'] is not None and int(group["group_id"]) == int(temp_user['group_id']):
                                            temp_user['group_name'] = group['group_name']
                                        if temp_user['group_id'] is None:
                                            temp_user['group_name'] = "Brak przypisanej grupy"
                                    temp_user['sla'] = sla
                                    temp_user['sla_start'] = temp_sla_start_date
                                    temp_user['sla_end'] = temp_sla_end_date
                                    temp_users_sla.append(temp_user.copy()) # COPY : O obiekty w pythonie są mutowalnej. jesli referencja tego samego obiektu jest dodawana wielokrotnie do listy to kazda zmiana obiektu powoduje zmiane wczesniejszych kopii
                                    if idx < len(audits):
                                        # print("idx", idx, "len(audits)", len(audits))
                                        recursion_audits = audits[idx + 1:]
                                        # print("Len recursion_audits:", len(recursion_audits))
                                        temp_sla_start_date = temp_sla_end_date
                                        temp_last_assigned_user = event["value"]
                                        temp_last_assigned_group = event["value"]
                                    else: 
                                        break
                                        
                                        # print("temp_users_sla:", temp_users_sla, "Dodać warunek na nastepne liczenie, rekurencja?, bo mamy dane startowa i nadal szukamy czegos pomiedzy cond_1-3")
                                        # temp_sla_start_date = temp_sla_end_date
                                        # print("Condition3, zmiana usera w trakcie SLA", temp_last_assigned_user, temp_last_assigned_group, temp_sla_start_date)
                                    pass
                                if sla <= 0: # CR: If we don't do anything with that condition, is it needed? Maybe a comment would be enough?
                                    break
                                    # print("Sla jest nieprzekroczone")
                                # print("Pobierz datę, policz sla do tej grupy/użytkownika z previous_value, nadpisz sla_start-date bo od tego momentu liczymy dla nowego użykownika")
                    pass
                    # print(audit['created_at'])
                    # print("123")
            # print("BBB", temp_users_sla)
            if temp_users_sla:
                temp_results['ticket_id'] = audits[0]['ticket_id']
                temp_results['users_sla'] = temp_users_sla
                temp_results['sum_sla'] = str(round(sum(item['sla'] for item in temp_results['users_sla'])/ 60, 2)).replace('.',',')
                temp_results['count_sla'] = len(temp_results['users_sla']) 

            else: # CR: If we don't do anything with that condition, is it needed? Maybe a comment would be enough?
                pass
                # print("No breached sla") 
            if(is_recursion):
                # print("temp_last_assigned_user", temp_last_assigned_user, "temp_last_assigned_group", temp_last_assigned_group)
                calculate_breached_sla(recursion_audits, temp_last_assigned_user, temp_last_assigned_group, temp_results, temp_users_sla, temp_user, temp_sla_is_breached_after, temp_sla_start_date, temp_sla_end_date)
                break
    # print(temp_results)
            # recursion_audits = audits[idx + 1:]
    return temp_results

# Loop over tickets and make audit for each
results = []
# ODKOMENTOWAĆ PO TESCIE #CR: EN pls
for idx,ticket_id in enumerate(updated_ticket_ids):
    ticket_audits = fetch_ticket_audits(ticket_id) #CR: Just a question: does Python ensure a proper order of sending related requests? Mean: don't we need any kind of "await/async" here?
    breached_results = calculate_breached_sla(ticket_audits['audits'])
    results.append(breached_results.copy())
    # print(results)
    print("Progress:", f"{idx} / {number_of_checked_tickets -1 }")
    # print(breached_results)
# ODKOMENTOWAC PO TESCIE #CR: EN pls

# TEST POJEDYNCZEGO TICKETU, trzeba tylko na poczatku kody zakomentowac blok z pobieraniem ticketow #CR: EN pls
# ticket_audits = fetch_ticket_audits(41645)
# breached_results = calculate_breached_sla(ticket_audits['audits'])
# results.append(breached_results.copy())
# END TEST

def find_longest_users_sla_length(results): #CR: Util function
    max_length = 0  
    for ticket in results:
        if 'users_sla' in ticket:
            users_sla_length = len(ticket['users_sla']) 
            if users_sla_length > max_length:
                max_length = users_sla_length
    return max_length

max_length = find_longest_users_sla_length(results)
# print("MAX_LENGTH:", max_length)
def export_to_csv(results):  #CR: Util function
    current_date = datetime.now().strftime('%Y-%m-%dT%H-%M-%SZ')
    # current_date = datetime.now().strftime('%Y-%m-%d')
    filename = f'Raport_SLA_{current_date}.csv'
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file, delimiter=';')
        headers = ['Numer Ticketu', 'Suma złamanych SLA [h]', 'Liczba złamanych SLA']
        for i in range(1, max_length +1):
            headers += [
                        f'Imię i nazwisko #{i}', f'Grupa #{i}', f'Przekroczone SLA #{i}' #, 
                        # f'sla_start_{i}', f'sla_end_{i}'
                    ]
        writer.writerow(headers)
        for item in results:
            if item:
                row = [item['ticket_id'], item['sum_sla'], item['count_sla']]
                for idx, user_sla in enumerate(item['users_sla']):
                        # print("ADFS", user_sla)
                        row += [
                            user_sla['name'],  
                            user_sla['group_name'],    
                            user_sla['sla'],        
                            #user_sla['sla_start'],  
                            #user_sla['sla_end']     
                            ]
                writer.writerow(row)
export_to_csv(results)

# ticket_audits = fetch_ticket_audits('41645') # 886 i 5
# ticket_audits = fetch_ticket_audits('41257') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('41265') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('41856') # tu nie było przekroczonych 
# ticket_audits = fetch_ticket_audits('40868') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('40085') # tu nie było przekroczonych
# ticket_audits = fetch_ticket_audits('39293') # 18
# ticket_audits = fetch_ticket_audits('41644') # mój 1636
# ticket_audits = fetch_ticket_audits('41551') # mój 362, 105, 152
# ticket_audits = fetch_ticket_audits('X') # tu nie było przekroczonych

#TO DO
# brak warunku na ticket w którym właśnie jest liczone SLA (przekroczone) i nic się więcej nie zadziało! z drugiej strony zawsze może dojść odpowiedź niewymagana
# brak warunku na krótki ticket w którym nikt nie został przypisany, a sla się liczyło i ktoś odpowiedział  40868
# do zrobienia w przyszłości, można wyrzucić ile każdy user/grupa ile miała złamanych sla i o ile i ile średnio np. zwrócić to w kolejnym arkuszu

# co do poprawy
# informacja ile ticketów zostało przeanalizowanych ile miało przekroczone SLA, %
# informacja z jakiego przedziału czasowego przeanalizowano tickety
# informacja ile ticketów miało złamane SLA o mniej niż 60min i o mniej niż 120min oraz o więcej niż 120min
# nie pokazuje nagłówków na górze dla userów f'Imię i nazwisko #{i}', f'Grupa #{i}', f'Przekroczone SLA #{i}' #, 
# ticket 41158 wyłapuje błąd, bierze internal wiadomość i liczy do niej >_< 
# makro do excela na poszerzanie kolumn, wysrodkowanie i kolorowanie
    # Private Sub Workbook_Open()
    #     Call DostosujSzerokośćKolumn
    # End Sub

    # Sub DostosujSzerokośćKolumn()
    #     Cells.EntireColumn.AutoFit
    # End Sub
    # Kolory HFT

    # RGB(255, 192, 203) 
    # RGB(173, 216, 230) 
    # RGB(144, 238, 144) 
    # RGB(240, 240, 240)
    # RGB(200, 200, 200)


# Error, ticket 41042 14:30 pisze klient, sla idzie, odpowiada Ewelina Zarzycka, ale ticket nie był do nikogo przypisany :D ani do grupy ani do usera
# Ticket 35427 Permanently deleted user to Adam Scibor id: 9479686926364 :D