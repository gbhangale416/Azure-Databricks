import os
import json
import logging
from datetime import datetime
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError

# Configure local console logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Azure Connection Setup ---
# Best Practice: Retrieve your connection string securely from environment variables
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

if not AZURE_STORAGE_CONNECTION_STRING:
    logging.warning("AZURE_STORAGE_CONNECTION_STRING environment variable is missing! Cloud operations will fail.")

# Initialize the global Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING) if AZURE_STORAGE_CONNECTION_STRING else None


# -----------------------------------------------------------------
# CLOUD INFRASTRUCTURE (Direct Azure Blob Storage SDK Connections)
# -----------------------------------------------------------------
def read_json_from_azure(container_name: str, blob_path: str) -> dict:
    """Helper utility to download and parse a JSON blob from a specific Azure Container."""
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
        download_stream = blob_client.download_blob()
        return json.loads(download_stream.readall().decode('utf-8'))
    except ResourceNotFoundError:
        logging.warning(f"Blob not found in cloud storage: container='{container_name}', path='{blob_path}'")
        return None
    except Exception as e:
        logging.error(f"Failed to read blob from Azure: {str(e)}")
        return None
