import random, string, sys
import requests

def __post_request(url, json_data):
    api_url = f"{api_host}/{url}"
    headers = {'X-API-Key': api_key, 'Content-type': 'application/json'}

    req = requests.post(api_url, headers=headers, json=json_data)
    rsp = req.json()
    req.close()

    if isinstance(rsp, list):
        rsp = rsp[0]

    if not "type" in rsp or not "msg" in rsp:
        sys.exit(f"API {url}: got response without type or msg from Mailcow API")
    
    if rsp['type'] != 'success':
        sys.exit(f"API {url}: {rsp['type']} - {rsp['msg']}")

def add_user(email, name, active):
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    json_data = {
        'local_part':email.split('@')[0],
        'domain':email.split('@')[1],
        'name':name,
        'password':password,
        'password2':password,
        "active": 1 if active else 0
    }

    __post_request('api/v1/add/mailbox', json_data)

def edit_user(email, active=None, name=None):
    attr = {}
    if (active is not None):
        attr['active'] = 1 if active else 0
    if (name is not None):
        attr['name'] = name

    json_data = {
        'items': [email],
        'attr': attr
    }

    __post_request('api/v1/edit/mailbox', json_data)

def __delete_user(email):
    json_data = [email]

    __post_request('api/v1/delete/mailbox', json_data)

def check_user(email):
    url = f"{api_host}/api/v1/get/mailbox/{email}"
    headers = {'X-API-Key': api_key, 'Content-type': 'application/json'}
    req = requests.get(url, headers=headers)
    rsp = req.json()
    req.close()
    
    if not isinstance(rsp, dict):
        sys.exit("API get/mailbox: got response of a wrong type")

    if (not rsp):
        return (False, False, None)

    if 'active_int' not in rsp and rsp['type'] == 'error':
        sys.exit(f"API {url}: {rsp['type']} - {rsp['msg']}")
    
    return (True, bool(rsp['active_int']), rsp['name'])

def get_domains():
    url = f"{api_host}/api/v1/get/domain/all"
    headers = {'X-API-Key': api_key, 'Content-type': 'application/json'}
    req = requests.get(url, headers=headers)
    rsp = req.json()
    req.close()
    
    if not isinstance(rsp, list):
        sys.exit("API get/domain/all: got response of a wrong type")
    
    # Extract domain names from the response
    domains = set()
    for domain_info in rsp:
        if 'domain_name' in domain_info:
            domains.add(domain_info['domain_name'])
    
    return domains