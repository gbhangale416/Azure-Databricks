import argparse
import requests

from config import (
    WORKSPACES,
    CLIENT_CREDENTIALS,
    LIFETIME_SECONDS
)


# ============================================================
# Arguments
# ============================================================

parser = argparse.ArgumentParser(
    description="Create Databricks PAT"
)

parser.add_argument(
    "--environment",
    required=True,
    choices=WORKSPACES.keys()
)

parser.add_argument(
    "--department",
    required=True,
    choices=["BIA", "CMO", "IDE"]
)

args = parser.parse_args()

environment = args.environment.lower()
department = args.department.upper()


# ============================================================
# Get Workspace
# ============================================================

host = WORKSPACES[environment]


# ============================================================
# Get Environment + Department Credentials
# ============================================================

try:
    credentials = CLIENT_CREDENTIALS[environment][department]

except KeyError:
    raise Exception(
        f"Credentials not configured for "
        f"environment={environment}, "
        f"department={department}"
    )


client_id = credentials["client_id"]
client_secret = credentials["client_secret"]


print("----------------------------------------")
print(f"Environment : {environment}")
print(f"Department  : {department}")
print(f"Workspace   : {host}")
print("----------------------------------------")


# ============================================================
# STEP 1
# Get OAuth Token
# ============================================================

oauth_url = f"{host}/oidc/v1/token"

oauth_data = {
    "grant_type": "client_credentials",
    "scope": "all-apis"
}


print("Getting OAuth token...")


oauth_response = requests.post(
    url=oauth_url,
    data=oauth_data,
    auth=(client_id, client_secret),
    timeout=60
)


if oauth_response.status_code != 200:

    print("OAuth Response:")
    print(oauth_response.text)

    raise Exception(
        f"OAuth token generation failed: "
        f"{oauth_response.status_code}"
    )


oauth_token = oauth_response.json()["access_token"]

print("OAuth token generated successfully.")


# ============================================================
# STEP 2
# Create Databricks PAT
# ============================================================

pat_url = f"{host}/api/2.0/token/create"


headers = {
    "Authorization": f"Bearer {oauth_token}",
    "Content-Type": "application/json"
}


payload = {
    "lifetime_seconds": LIFETIME_SECONDS,
    "comment": f"{environment.upper()} {department} PAT"
}


print("Creating Databricks PAT...")


pat_response = requests.post(
    url=pat_url,
    headers=headers,
    json=payload,
    timeout=60
)


# ============================================================
# STEP 3
# Validate
# ============================================================

if pat_response.status_code not in [200, 201]:

    print("PAT Response:")
    print(pat_response.text)

    raise Exception(
        f"PAT creation failed: "
        f"{pat_response.status_code}"
    )


# ============================================================
# STEP 4
# Get actual PAT
# ============================================================

pat_details = pat_response.json()

token_id = pat_details.get("token_id")
token_value = pat_details.get("token_value")


# ============================================================
# Result
# ============================================================

print()
print("========================================")
print("PAT CREATED SUCCESSFULLY")
print("========================================")

print(f"Environment : {environment}")
print(f"Department  : {department}")
print(f"Workspace   : {host}")
print(f"Token ID    : {token_id}")
print(f"PAT Token   : {token_value}")

print("========================================")
