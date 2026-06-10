import os
import json
import logging
from azure.storage.blob import BlobClient

# Configure tracking log output format properties
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verify_local_against_azure_target(db_name: str, target_container: str, local_output_path: str):
    """
    Downloads the actual deployment target file from Azure Blob Storage 
    and compares it key-by-key against your locally generated output file.
    """
    # 1. Fetch Connection String from Environment
    connection_string = os.environ.get('AzureBlobStorageConnectionString')
    if not connection_string:
        logging.error("Missing Environment Variable: 'AzureBlobStorageConnectionString' is not set.")
        print("\n[!] Please run this in your terminal before executing:")
        print("    export AzureBlobStorageConnectionString='your_actual_connection_string'\n")
        return

    # 2. Establish Remote Target Client
    blob_name = f"{db_name}/{db_name}_metameta.json"
    logging.info(f"Connecting to container '{target_container}' to fetch remote target file: '{blob_name}'...")
    
    try:
        blob_client = BlobClient.from_connection_string(
            connection_string,
            container_name=target_container,
            blob_name=blob_name
        )
        
        if not blob_client.exists():
            logging.warning(f"The file '{blob_name}' does not exist in target container '{target_container}'. This is a new deployment.")
            return

        # Download and deserialize remote structure
        remote_data_stream = blob_client.download_blob()
        remote_json = json.loads(remote_data_stream.content_as_text())
        logging.info("Successfully downloaded remote target metadata file.")
        
    except Exception as e:
        logging.error(f"Failed to pull file from Azure Storage: {e}")
        return

    # 3. Read Locally Generated Metameta Output File
    if not os.path.exists(local_output_path):
        logging.error(f"Local file not found at: '{local_output_path}'. Run your local script first.")
        return

    with open(local_output_path, 'r') as f:
        local_json = json.load(f)

    # 4. Run Structural Comparison Engine
    print("\n" + "="*60)
    print(f" METAMETA VERIFICATION REPORT: {db_name.upper()} ")
    print("="*60)

    # Compare top level root properties
    mismatches = 0
    root_keys = set(list(local_json.keys()) + list(remote_json.keys()))
    
    for key in sorted(root_keys):
        if key == 'entities':
            continue  # Entities handled separately below
            
        local_val = local_json.get(key, "MISSING")
        remote_val = remote_json.get(key, "MISSING")
        
        if local_val != remote_val:
            mismatches += 1
            print(f"[⚠️ MISMATCH] Root Property: '{key}'")
            print(f"    -> Local Generated: {local_val}")
            print(f"    -> Remote Azure:   {remote_val}")

    # Compare nested entity configurations
    local_entities = {e['source_entity'].lower(): e for e in local_json.get('entities', [])}
    remote_entities = {e['source_entity'].lower(): e for e in remote_json.get('entities', [])}

    all_entity_names = set(list(local_entities.keys()) + list(remote_entities.keys()))
    
    for ent_name in sorted(all_entity_names):
        if ent_name not in remote_entities:
            mismatches += 1
            print(f"[➕ NEW ENTITY] '{ent_name}' is locally added but doesn't exist in Azure yet.")
            continue
        if ent_name not in local_entities:
            mismatches += 1
            print(f"[❌ REMOVED ENTITY] '{ent_name}' exists in Azure but was skipped/removed locally.")
            continue

        # If entity exists in both, compare internal parameter mappings
        l_ent = local_entities[ent_name]
        r_ent = remote_entities[ent_name]
        
        ent_keys = set(list(l_ent.keys()) + list(r_ent.keys()))
        for e_key in ent_keys:
            if l_ent.get(e_key) != r_ent.get(e_key):
                mismatches += 1
                print(f"[⚠️ MISMATCH] Entity '{ent_name}' -> Property '{e_key}':")
                print(f"    -> Local Generated: {l_ent.get(e_key)}")
                print(f"    -> Remote Azure:   {r_ent.get(e_key)}")

    print("="*60)
    if mismatches == 0:
        print("✅ SUCCESS: Local configuration matches Azure target container perfectly!")
    else:
        print(f"❌ VERIFICATION COMPLETED: Found {mismatches} discrepancy/difference(s).")
    print("="*60 + "\n")


if __name__ == "__main__":
    # --- Execution Testing Setup ---
    # Change these values to match your specific target configuration context params
    TARGET_DATABASE = "my_database"
    TARGET_CONTAINER_NAME = "your-actual-target-container-name"
    
    # Path where your local runner dropped its output
    LOCAL_GENERATED_FILE = os.path.join(os.getcwd(), "mock_storage", TARGET_DATABASE, f"{TARGET_DATABASE}_metameta.json")

    verify_local_against_azure_target(
        db_name=TARGET_DATABASE,
        target_container=TARGET_CONTAINER_NAME,
        local_output_path=LOCAL_GENERATED_FILE
    )
