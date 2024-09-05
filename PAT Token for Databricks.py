import requests

# Step 1: Get OAuth Token from Azure AD
def get_oauth_token(tenant_id, client_id, client_secret):
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "client_id": client_id,
        "scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",  # Azure Databricks scope
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        raise Exception(f"Failed to get OAuth token: {response.status_code}, {response.text}")

# Step 2: Create a PAT Token for Databricks
def create_pat_token(databricks_instance, oauth_token, lifetime_seconds, comment):
    url = f"https://{databricks_instance}/api/2.0/token/create"
    
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "lifetime_seconds": lifetime_seconds,
        "comment": comment
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json().get('token_value')
    else:
        raise Exception(f"Failed to create PAT token: {response.status_code}, {response.text}")

# Example usage
tenant_id = "<TENANT_ID>"
client_id = "<SERVICE_PRINCIPAL_CLIENT_ID>"
client_secret = "<SERVICE_PRINCIPAL_CLIENT_SECRET>"
databricks_instance = "<DATABRICKS_INSTANCE>"  # e.g., "adb-1234.12.azuredatabricks.net"
lifetime_seconds = 31536000  # 1 year in seconds (365 days)
comment = "Token for Service Principal"

try:
    # Step 1: Get OAuth Token
    oauth_token = get_oauth_token(tenant_id, client_id, client_secret)
    print(f"OAuth Token: {oauth_token}")
    
    # Step 2: Create PAT Token
    pat_token = create_pat_token(databricks_instance, oauth_token, lifetime_seconds, comment)
    print(f"PAT Token: {pat_token}")
except Exception as e:
    print(str(e))
