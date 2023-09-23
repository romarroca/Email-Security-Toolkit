import re
import requests
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode
import json
import html
import sys
import getpass
import os


def fetch_sender_maturity_quarantine(end_date, start_date, esa_ip):
    base_url = "https://{your_cisco_sma_url_here}/sma/api/v2.0/quarantine/messages?"
    query_params = {
        "endDate": end_date,
        "limit": 100,
        "offset": 0,
        "orderBy": "sender",
        "orderDir": "desc",
        "quarantineType": "pvo",
        "quarantines": "sender-maturity",  
        "startDate": start_date,
        "originatingEsaIp": esa_ip
    }
    encoded_params = urlencode(query_params)
    final_url = f"{base_url}{encoded_params}"
    return final_url

def fetch_email_details(mid, username, password):
    detail_url_email = "https://{your_cisco_sma_url_here}/sma/api/v2.0/quarantine/messages/details?"
    query_params_email = {
        "quarantineType": "pvo",
        "mid": mid
    }
    encoded_params = urlencode(query_params_email)
    final_url_email = f"{detail_url_email}{encoded_params}"
    response = requests.get(final_url_email, headers=headers, auth=HTTPBasicAuth(f'{username}', f'{password}'))
    
    #print(f"Debug: fetch_email_details status code: {response.status_code}")

    quarantine_names = []
    if response.status_code == 200:
        response_data = response.json()
        #print(f"Debug: Full response_data = {json.dumps(response_data, indent=4)}")  # Debugging line
        attributes = response_data.get('data', {}).get('attributes', {})
        quarantine_details = attributes.get('quarantineDetails', [])
        for entry in quarantine_details:
            quarantine_name = entry.get('quarantineName', None)
            if quarantine_name:
                quarantine_names.append(quarantine_name)
        
        # data = response.text
        header_details = attributes.get('headers', [])
        match = re.search(r"Received: from (.*?)<br>", header_details)
        if match:
            sender_detail = match.group(1)
        
        message_body = attributes.get('messageBody', None)
        return sender_detail, quarantine_names, message_body
    return None, [], None

def release_email(input_mid_release, username, password):
    release_url_email = "https://{your_cisco_sma_url_here}/sma/api/v2.0/quarantine/messages"
    
    headers = {
        "Content-Type": "application/json"
    }

    try:
        mid_value = int(input_mid_release)  # Explicitly convert MID to integer
    except ValueError:
        print("Invalid MID value. Please enter a valid integer.")
        return
    
    payload = {
        "action": "release",
        "mids": [mid_value],
        "quarantineName": "sender-maturity",
        "quarantineType": "pvo"
    }
    
    response_release = requests.post(
        release_url_email, 
        headers=headers, 
        auth=HTTPBasicAuth(username, password),
        json=payload
    )

    if response_release.status_code == 200:
        print("Successfully released the email.")
    else:
        print(f"Failed to release the email. Status code: {response_release.status_code}")

    return response_release.status_code

def cleanup_files():
    choice = input("Do you want to clean up the generated HTML files? (y/n): ")
    if choice.lower() == 'y':
        files_to_remove = [f for f in os.listdir() if f.startswith("message_body_") and f.endswith(".html")]
        for file in files_to_remove:
            os.remove(file)
            print(f"Removed {file}")

if __name__ == "__main__":
    esa_ips = ["A.B.C.D", "E.F.G.H"] # Change this value to the IP address of your ESA, you can add more IP here
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    current_time = datetime.utcnow().replace(second=0, microsecond=0)
    end_date = current_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    start_date = (current_time - timedelta(days=1)).replace(second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    
    headers = {
        "Content-Type": "application/json"
    }

    for esa_ip in esa_ips:
        final_url = fetch_sender_maturity_quarantine(end_date, start_date, esa_ip)
        response = requests.get(final_url, headers=headers, auth=HTTPBasicAuth(f'{username}', f'{password}'))
        #print(f"working on ESA IP: {esa_ip}") # Debugging line
        if response.status_code == 200:
            response_data = response.json()
            for entry in response_data['data']:
                attributes = entry.get('attributes', {})
                mid = entry.get('mid', '')
                #print(f"Debug: Using mid = {mid}")  # Debugging line
                
                # Fetch additional email details first to get quarantine names
                sender_detail, quarantine_names, message_body = fetch_email_details(mid, username, password)
                #print(f"Debug: Conditions met. Quarantine names: {quarantine_names}")  # Debugging line
                
                if len(quarantine_names) == 1 and 'sender-maturity' in quarantine_names:
                    sender = attributes.get('sender', '')
                    recipients = ', '.join(attributes.get('recipient', []))
                    subject = attributes.get('subject', '')
                    print(f"Sender: {sender}")
                    print(f"Recipient/s: {recipients}")
                    print(f"Subject: {subject}")
                    print(f"Mail id: {mid}")
                    print(f"Sender Detail from email header: {sender_detail}")
                    print(f"Quarantine Reason: {', '.join(quarantine_names)}")
                    if message_body:
                        filename = f"message_body_{sender}_{mid}.html"
                        with open(filename, "w", encoding='utf-8') as f:
                            f.write("<html><body><pre>\n")
                            f.write(message_body)
                            f.write("\n</pre></body></html>")
                       
                    print("-------")
                else:
                    pass #print(f"Debug: Conditions not met. Quarantine names: {quarantine_names}")  # Debugging line
        else:
            print(f"Failed to fetch data: {response.status_code}")
    
    input_mid_release = input("Input the Mail id you want to release or type quit to exit: ")

    if input_mid_release == "quit":
        cleanup_files()
        print("Goodbye!")
        sys.exit(0)
    else:
        release_email(input_mid_release, username, password)
        cleanup_files()
