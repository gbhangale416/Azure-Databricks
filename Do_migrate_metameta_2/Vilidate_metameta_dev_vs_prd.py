import csv
import json
import logging
import os
from azure.storage.blob import BlobServiceClient, BlobClient

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def get_azure_json(connection_string: str, container_name: str, blob_path: str) -> dict:
    """Safely fetches and parses a JSON file directly from Azure Blob Storage."""
    try:
        if not connection_string or connection_string == "your_connection_string_here":
            raise ValueError("Connection string is placeholder or empty.")

        blob_client = BlobClient.from_connection_string(
            connection_string,
            container_name=container_name,
            blob_name=blob_path,
        )
        blob_data = blob_client.download_blob()
        return json.loads(blob_data.content_as_text())
    except Exception as e:
        logging.error(f"Failed to fetch JSON from {container_name}/{blob_path}: {e}")
        return None


def list_dev_databases(connection_string: str, container_name: str) -> list:
    """
    Scans the Dev container to find all distinct database folders 
    by looking for '_metameta.json' files.
    """
    db_names = set()
    try:
        if not connection_string or connection_string == "your_connection_string_here":
            raise ValueError("Dev connection string is placeholder or empty.")

        service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = service_client.get_container_client(container_name)
        
        blobs = container_client.list_blobs()
        for blob in blobs:
            # Expecting path structure: db_name/db_name_metameta.json
            if blob.name.endswith("_metameta.json"):
                # Extract the top-level folder / database name
                parts = blob.name.split("/")
                if len(parts) > 1:
                    db_names.add(parts[0])
                    
        return sorted(list(db_names))
    except Exception as e:
        logging.critical(f"Could not discover database folders from Dev container: {e}")
        return []


def calculate_deep_diff(dev_obj: dict, prd_obj: dict, path="") -> tuple:
    """
    Recursively tracks down exact differences between two nested JSON objects.
    Returns: (added_list, removed_list, modified_list)
    """
    added, removed, modified = [], [], []

    if isinstance(dev_obj, dict) and isinstance(prd_obj, dict):
        # Check keys present in DEV but missing in PRD
        for k in dev_obj:
            current_path = f"{path}.{k}" if path else k
            if k not in prd_obj:
                added.append(current_path)
            else:
                # Key matches, check deeper recursively
                a, r, m = calculate_deep_diff(dev_obj[k], prd_obj[k], current_path)
                added.extend(a)
                removed.extend(r)
                modified.extend(m)
                
        # Check keys present in PRD but missing in DEV
        for k in prd_obj:
            current_path = f"{path}.{k}" if path else k
            if k not in dev_obj:
                removed.append(current_path)

    elif isinstance(dev_obj, list) and isinstance(prd_obj, list):
        # Fallback comparison for arrays/lists
        if dev_obj != prd_obj:
            modified.append(f"{path} (Array structure changed)")
            
    else:
        # Direct primitive value mismatch evaluation
        if dev_obj != prd_obj:
            modified.append(f"{path} ('{dev_obj}' vs '{prd_obj}')")

    return added, removed, modified


def verify_metadata(
    dev_conn: str, dev_container: str, 
    prd_conn: str, prd_container: str, 
    db_name: str, file_name="metameta"
) -> dict:
    """Compares DEV configurations to PRD configurations down to the sub-key level."""
    report_record = {
        "Database": db_name,
        "Status": "PENDING",
        "Details": "",
        "Added Details": "",
        "Removed Details": "",
        "Modified Value Details": ""
    }

    blob_path = f"{db_name}/{db_name}_{file_name}.json"

    try:
        # Fetching both JSON files directly from their respective Azure locations
        dev_json = get_azure_json(dev_conn, dev_container, blob_path)
        prd_json = get_azure_json(prd_conn, prd_container, blob_path)

        if dev_json is None or prd_json is None:
            reasons = []
            if dev_json is None: reasons.append("Dev Azure blob missing/failed")
            if prd_json is None: reasons.append("Prd Azure blob missing/failed")
            report_record["Status"] = "ABORTED"
            report_record["Details"] = " & ".join(reasons)
            return report_record

        print("\n" + "=" * 60)
        print(f" METAMETA VERIFICATION REPORT: {db_name.upper()} ")
        print("=" * 60)

        if dev_json == prd_json:
            print(f"SUCCESS: Perfect match for {db_name.upper()}!")
            report_record["Status"] = "SUCCESS"
            report_record["Details"] = "Perfect configuration symmetry between DEV and PRD."
        else:
            print(f"MISMATCH DETECTED: Calculating nested mutations...")
            report_record["Status"] = "MISMATCH"
            report_record["Details"] = "Structural or interior configuration value drift."

            # Run the deep discovery differentiator 
            added_paths, removed_paths, modified_paths = calculate_deep_diff(dev_json, prd_json)

            if added_paths:
                print(f" -> Added in DEV (Missing in PRD): {added_paths}")
                report_record["Added Details"] = " | ".join(added_paths)
            if removed_paths:
                print(f" -> Missing in DEV (Present in PRD): {removed_paths}")
                report_record["Removed Details"] = " | ".join(removed_paths)
            if modified_paths:
                print(f" -> Changed values: {modified_paths}")
                report_record["Modified Value Details"] = " | ".join(modified_paths)

        print("=" * 60 + "\n")
        return report_record

    except Exception as e:
        logging.error(f"Unexpected internal error executing profile '{db_name}': {e}")
        report_record["Status"] = "FAILED"
        report_record["Details"] = f"Runtime Error: {str(e)}"
        return report_record


if __name__ == "__main__":
    # --- Connection Configuration ---
    # Update these with your target environment parameters
    DEV_CONNECTION_STRING = "your_dev_connection_string_here"
    PRD_CONNECTION_STRING = "your_prd_connection_string_here"
    
    DEV_CONTAINER_NAME = "metadata-dev"
    PRD_CONTAINER_NAME = "metadata-prd"
    
    # Report compilation local output path
    LOCAL_REPORT_ROOT = os.path.join(os.getcwd(), "mock_storage")
    
    csv_results = []

    # 1. Dynamically scan Dev container folders 
    print("Scanning Dev container for databases...")
    db_folders = list_dev_databases(DEV_CONNECTION_STRING, DEV_CONTAINER_NAME)

    if not db_folders:
        print(f"\n[!] Complete: No database metadata profiles discovered in container: '{DEV_CONTAINER_NAME}'")
    else:
        print(f"--- Found {len(db_folders)} profile(s) in DEV to process: {db_folders} ---\n")

        # 2. Iterate and compare Dev blobs sequentially against Prod blobs
        for db_name_target in db_folders:
            try:
                result = verify_metadata(
                    dev_conn=DEV_CONNECTION_STRING,
                    dev_container=DEV_CONTAINER_NAME,
                    prd_conn=PRD_CONNECTION_STRING,
                    prd_container=PRD_CONTAINER_NAME,
                    db_name=db_name_target
                )
                csv_results.append(result)

            except Exception as loop_exception:
                logging.error(f"Critical iteration failure on '{db_name_target}': {loop_exception}")
                csv_results.append({
                    "Database": db_name_target, "Status": "CRASHED",
                    "Details": f"Loop crash: {str(loop_exception)}",
                    "Added Details": "", "Removed Details": "", "Modified Value Details": ""
                })

        # --- Generate Exhaustive CSV Report ---
        csv_file_path = os.path.join(LOCAL_REPORT_ROOT, "detailed_difference_report.csv")
        csv_headers = ["Database", "Status", "Details", "Added Details", "Removed Details", "Modified Value Details"]

        try:
            os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
            with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
                writer.writeheader()
                writer.writerows(csv_results)
            print(f"[+] Detailed analytics report compiled at: {csv_file_path}")
        except Exception as e:
            logging.critical(f"Failed to save CSV file: {e}")
