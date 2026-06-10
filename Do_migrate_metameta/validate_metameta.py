import os
import json
import logging
from azure.storage.blob import BlobClient

# Configure uniform logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_remote_json(connection_string: str, container_name: str, blob_name: str) -> dict:
    """Downloads and parses JSON directly from Azure Blob Storage."""
    try:
        blob_client = BlobClient.from_connection_string(
            conn_str=connection_string, 
            container_name=container_name, 
            blob_name=blob_name
        )
        
        if not blob_client.exists():
            logging.warning(f"Remote file '{blob_name}' not found in container '{container_name}'.")
            return {}

        logging.info(f"Downloading remote file: {blob_name}")
        stream = blob_client.download_blob()
        return json.loads(stream.content_as_text())
        
    except Exception as e:
        logging.error(f"Error fetching remote Azure blob: {e}")
        return {}

def get_local_json(file_path: str) -> dict:
    """Reads and parses a local JSON file."""
    if not os.path.exists(file_path):
        logging.error(f"Local file not found at: '{file_path}'")
        return {}
    
    with open(file_path, 'r') as f:
        return json.load(f)

def verify_metadata(db_name: str, target_container: str, local_output_path: str):
    """Fetches local and remote JSON configurations and compares them."""
    
    # 1. Get Connection String
    conn_str = os.environ.get('AzureBlobStorageConnectionString')
    if not conn_str:
        logging.error("Environment variable 'AzureBlobStorageConnectionString' is missing.")
        return

    # 2. Retrieve both JSON objects
    blob_name = f"{db_name}/{db_name}_metameta.json"
    remote_json = get_remote_json(conn_str, target_container, blob_name)
    local_json = get_local_json(local_output_path)

    if not remote_json or not local_json:
        logging.error("Verification aborted: Could not load one or both JSON payloads.")
        return

    # 3. Direct Equivalence Validation
    print("\n" + "="*60)
    print(f" METAMETA VERIFICATION REPORT: {db_name.upper()} ")
    print("="*60)
    
    if local_json == remote_json:
        logging.info("✅ SUCCESS: Local configuration matches Azure perfectly!")
    else:
        logging.warning("❌ MISMATCH DETECTED: Local and remote configurations differ.")
        
        # Pull top-level structure changes using sets
        added_keys = set(local_json.keys()) - set(remote_json.keys())
        removed_keys = set(remote_json.keys()) - set(local_json.keys())
        
        if added_keys:   print(f" -> Keys added locally: {list(added_keys)}")
        if removed_keys: print(f" -> Keys missing locally: {list(removed_keys)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Update these configuration values to match your environments
    TARGET_DATABASE = "my_database"
    TARGET_CONTAINER_NAME = "your-actual-target-container-name"
    
    # Absolute path setup
    LOCAL_GENERATED_FILE = os.path.join(
        os.getcwd(), 
        "mock_storage", 
        TARGET_DATABASE, 
        f"{TARGET_DATABASE}_metameta.json"
    )

    verify_metadata(
        db_name=TARGET_DATABASE,
        target_container=TARGET_CONTAINER_NAME,
        local_output_path=LOCAL_GENERATED_FILE
    )
