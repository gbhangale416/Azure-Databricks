# ============================================================
# Databricks Workspace Configuration
# ============================================================

WORKSPACES = {
    "dev": "https://<DEV-WORKSPACE>.azuredatabricks.net",
    "test": "https://<TST-WORKSPACE>.azuredatabricks.net",
    "prod": "https://<PROD-WORKSPACE>.azuredatabricks.net"
}


# ============================================================
# Department Client Credentials
# ============================================================

CLIENT_CREDENTIALS = {
    "BIA": {
        "client_id": "<BIA_CLIENT_ID>",
        "client_secret": "<BIA_CLIENT_SECRET>"
    },

    "CMO": {
        "client_id": "<CMO_CLIENT_ID>",
        "client_secret": "<CMO_CLIENT_SECRET>"
    },

    "IDE": {
        "client_id": "<IDE_CLIENT_ID>",
        "client_secret": "<IDE_CLIENT_SECRET>"
    }
}


# ============================================================
# PAT Configuration
# ============================================================

LIFETIME_SECONDS = 31536000  # 1 year
