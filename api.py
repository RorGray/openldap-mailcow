import random, string, sys
import requests
import logging
import socket

def __post_request(url, json_data):
    api_url = f"{api_host}/{url}"
    headers = {'X-API-Key': api_key, 'Content-type': 'application/json'}

    try:
        req = requests.post(api_url, headers=headers, json=json_data)
        
        # Check HTTP status code first
        if req.status_code == 401:
            source_ip = __get_source_ip()
            raise Exception(f"API authentication failed (401 Unauthorized). URI: {api_url} | Source IP: {source_ip} | Please check your API_KEY.")
        elif req.status_code == 403:
            source_ip = __get_source_ip()
            raise Exception(f"API access forbidden (403 Forbidden). URI: {api_url} | Source IP: {source_ip} | Please check that IP {source_ip} is allowed to access the Mailcow API and has read-write permissions.")
        elif req.status_code >= 400:
            raise Exception(f"API request failed with HTTP {req.status_code}. URI: {api_url} | Response: {req.text[:200]}")
        
        # Try to parse JSON
        try:
            rsp = req.json()
        except requests.exceptions.JSONDecodeError as e:
            source_ip = __get_source_ip()
            raise Exception(f"API returned non-JSON response (status {req.status_code}). URI: {api_url} | Source IP: {source_ip} | This often means API access is denied or IP is not allowed. Response content: {req.text[:200]}")
        finally:
            req.close()

        if isinstance(rsp, list):
            rsp = rsp[0]

        if not "type" in rsp or not "msg" in rsp:
            raise Exception(f"API {url}: got response without type or msg from Mailcow API. URI: {api_url}")
        
        if rsp['type'] != 'success':
            raise Exception(f"API {url}: {rsp['type']} - {rsp['msg']} | URI: {api_url}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)} | URI: {api_url}")

def __get_source_ip():
    """Get the source IP address that will be used for outgoing requests to the Mailcow API"""
    try:
        # Extract hostname and port from api_host
        from urllib.parse import urlparse
        parsed = urlparse(api_host)
        hostname = parsed.hostname or api_host.split('://')[1].split(':')[0] if '://' in api_host else api_host.split(':')[0]
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        # Create a socket to determine which local IP would be used to connect to Mailcow
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to the Mailcow host (doesn't actually send data, just determines routing)
        s.connect((hostname, port))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "unknown"

def generate_secure_password(length=64):
    """
    Generate a secure password that fulfills all Mailcow password requirements
    and avoids a bad password error on mailbox creation. Specifically:
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one digit
    - At least one special character
    - Configurable length (default: 64 characters)

    Returns:
        str: A randomly generated secure password
    """
    special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'

    # Ensure at least one of each required character type for Mailcow compatibility
    password_parts = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(special_chars)
    ]

    # Fill the remainder of the password with random characters from all sets
    all_chars = string.ascii_letters + string.digits + special_chars
    remaining_length = length - len(password_parts)
    password_parts.extend(random.choices(all_chars, k=remaining_length))

    # Shuffle to prevent predictable order
    random.shuffle(password_parts)
    return ''.join(password_parts)

def add_user(email, name, active, authsource='ldap'):
    password = generate_secure_password()
    json_data = {
        'local_part':email.split('@')[0],
        'domain':email.split('@')[1],
        'name':name,
        'authsource':authsource,
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
    
    try:
        req = requests.get(url, headers=headers)
        
        # Check HTTP status code first
        if req.status_code == 401:
            source_ip = __get_source_ip()
            raise Exception(f"API authentication failed (401 Unauthorized). URI: {url} | Source IP: {source_ip} | Please check your API_KEY.")
        elif req.status_code == 403:
            source_ip = __get_source_ip()
            raise Exception(f"API access forbidden (403 Forbidden). URI: {url} | Source IP: {source_ip} | Please check that IP {source_ip} is allowed to access the Mailcow API and has read-write permissions.")
        elif req.status_code >= 400:
            raise Exception(f"API request failed with HTTP {req.status_code}. URI: {url} | Response: {req.text[:200]}")
        
        # Try to parse JSON
        try:
            rsp = req.json()
        except requests.exceptions.JSONDecodeError as e:
            source_ip = __get_source_ip()
            raise Exception(f"API returned non-JSON response (status {req.status_code}). URI: {url} | Source IP: {source_ip} | This often means API access is denied or IP is not allowed. Response content: {req.text[:200]}")
        finally:
            req.close()
        
        if not isinstance(rsp, dict):
            raise Exception(f"API get/mailbox: got response of wrong type (expected dict, got {type(rsp).__name__}). URI: {url}")

        if (not rsp):
            return (False, False, None)

        if 'active_int' not in rsp and rsp['type'] == 'error':
            raise Exception(f"API {url}: {rsp['type']} - {rsp['msg']} | URI: {url}")
        
        return (True, bool(rsp['active_int']), rsp['name'])
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)} | URI: {url}")

def get_domains():
    url = f"{api_host}/api/v1/get/domain/all"
    headers = {'X-API-Key': api_key, 'Content-type': 'application/json'}
    
    try:
        req = requests.get(url, headers=headers)
        
        # Check HTTP status code first
        if req.status_code == 401:
            source_ip = __get_source_ip()
            raise Exception(f"API authentication failed (401 Unauthorized). URI: {url} | Source IP: {source_ip} | Please check your API_KEY.")
        elif req.status_code == 403:
            source_ip = __get_source_ip()
            raise Exception(f"API access forbidden (403 Forbidden). URI: {url} | Source IP: {source_ip} | Please check that IP {source_ip} is allowed to access the Mailcow API and has read-write permissions.")
        elif req.status_code >= 400:
            raise Exception(f"API request failed with HTTP {req.status_code}. URI: {url} | Response: {req.text[:200]}")
        
        # Try to parse JSON
        try:
            rsp = req.json()
        except requests.exceptions.JSONDecodeError as e:
            source_ip = __get_source_ip()
            raise Exception(f"API returned non-JSON response (status {req.status_code}). URI: {url} | Source IP: {source_ip} | This often means API access is denied or IP is not allowed. Response content: {req.text[:200]}")
        finally:
            req.close()
        
        if not isinstance(rsp, list):
            raise Exception(f"API get/domain/all: got response of wrong type (expected list, got {type(rsp).__name__}). URI: {url}")
        
        # Extract domain names from the response
        domains = set()
        for domain_info in rsp:
            if 'domain_name' in domain_info:
                domains.add(domain_info['domain_name'])
        
        return domains
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)} | URI: {url}")