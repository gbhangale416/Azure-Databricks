# ============================================================
# Databricks Workspace URL
# Same URL for all departments in an environment
# ============================================================

WORKSPACES = {
    "dev": "https://<DEV-WORKSPACE>.azuredatabricks.net",
    "test": "https://adb-4433143851805380.0.azuredatabricks.net",
    "prod": "https://<PROD-WORKSPACE>.azuredatabricks.net"
}


# ============================================================
# Client Credentials
# Different credentials for each Environment + Department
# ============================================================

CLIENT_CREDENTIALS = {

    "dev": {

        "BIA": {
            "client_id": "<DEV_BIA_CLIENT_ID>",
            "client_secret": "<DEV_BIA_CLIENT_SECRET>"
        },

        "CMO": {
            "client_id": "<DEV_CMO_CLIENT_ID>",
            "client_secret": "<DEV_CMO_CLIENT_SECRET>"
        },

        "IDE": {
            "client_id": "<DEV_IDE_CLIENT_ID>",
            "client_secret": "<DEV_IDE_CLIENT_SECRET>"
        }
    },


    "test": {

        "BIA": {
            "client_id": "<TEST_BIA_CLIENT_ID>",
            "client_secret": "<TEST_BIA_CLIENT_SECRET>"
        },

        "CMO": {
            "client_id": "<TEST_CMO_CLIENT_ID>",
            "client_secret": "<TEST_CMO_CLIENT_SECRET>"
        },

        "IDE": {
            "client_id": "<TEST_IDE_CLIENT_ID>",
            "client_secret": "<TEST_IDE_CLIENT_SECRET>"
        }
    },


    "prod": {

        "BIA": {
            "client_id": "<PROD_BIA_CLIENT_ID>",
            "client_secret": "<PROD_BIA_CLIENT_SECRET>"
        },

        "CMO": {
            "client_id": "<PROD_CMO_CLIENT_ID>",
            "client_secret": "<PROD_CMO_CLIENT_SECRET>"
        },

        "IDE": {
            "client_id": "<PROD_IDE_CLIENT_ID>",
            "client_secret": "<PROD_IDE_CLIENT_SECRET>"
        }
    }
}


# ============================================================
# PAT Configuration
# ============================================================

LIFETIME_SECONDS = 31536000  # 365 days
