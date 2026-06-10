import csv
import json
import logging
import os
from azure.storage.blob import BlobClient

# Mock/Global setup assumed from your script
TARGET_ROOT = ""  # Will be overridden in main block


def get_remote_json(
    connection_string: str,
    db_name: str,
    container_name: str,
    file_name="metameta",
) -> dict:
    try:
        metameta_blob_client = BlobClient.from_connection_string(
            connection_string,
            container_name=container_name,
            blob_name=f"{db_name}/{db_name}_{file_name}.json",
        )

        metameta_ssdl = metameta_blob_client.download_blob()
        metameta_blob_text = metameta_ssdl.content_as_text()
        metameta_dict = json.loads(metameta_blob_text)
        return metameta_dict
    except Exception as e:
        logging.error(f"Failed to fetch remote JSON for {db_name}: {e}")
        return None


def get_local_tgt_metameta(db_name: str):
    path = os.path.join(TARGET_ROOT, db_name, f"{db_name}_metameta.json")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(
            f"Local target metameta file not found at: {path}. Assuming fresh run."
        )
        return None


def verify_metadata(
    connection_string: str,
    db_name: str,
    container_name: str,
    file_name="metameta",
) -> dict:
    """Verifies local vs remote metadata and returns a dictionary summary of the result."""
    remote_json = get_remote_json(
        connection_string, db_name, container_name, file_name="metameta"
    )
    local_json = get_local_tgt_metameta(db_name)

    # Base report record structure
    report_record = {
        "Database": db_name,
        "Status": "PENDING",
        "Details": "",
        "Added Keys": "",
        "Removed Keys": "",
    }

    if not remote_json or not local_json:
        error_msg = "Verification aborted: Could not load one or both JSON payloads."
        logging.error(error_msg)
        report_record["Status"] = "ERROR"
        report_record["Details"] = (
            "Missing local configuration"
            if not local_json
            else "Missing remote blob"
        )
        return report_record

    print("\n" + "=" * 60)
    print(f" METAMETA VERIFICATION REPORT: {db_name.upper()} ")
    print("=" * 60)

    if local_json == remote_json:
        print(f"SUCCESS: Local configuration matches Azure perfectly! For : {db_name.upper()}")
        report_record["Status"] = "SUCCESS"
        report_record["Details"] = "Local configuration matches Azure perfectly."
    else:
        logging.warning("MISMATCH DETECTED: Local and remote configurations differ.")
        report_record["Status"] = "MISMATCH"
        report_record["Details"] = "Local and remote configurations differ."

        # Pull top-level structure changes using sets
        added_keys = set(local_json.keys()) - set(remote_json.keys())
        removed_keys = set(remote_json.keys()) - set(local_json.keys())

        if added_keys:
            print(f" -> Keys added locally: {list(added_keys)}")
            report_record["Added Keys"] = ", ".join(list(added_keys))
        if removed_keys:
            print(f" -> Keys missing locally: {list(removed_keys)}")
            report_record["Removed Keys"] = ", ".join(list(removed_keys))

    print("=" * 60 + "\n")
    return report_record


if __name__ == "__main__":
    # --- Execution Testing Setup ---
    connection_string = "your_connection_string_here"
    LOCAL_STORAGE_ROOT = os.path.join(os.getcwd(), "mock_storage")
    SOURCE_ROOT = os.path.join(LOCAL_STORAGE_ROOT, "source", "metadata")
    TARGET_ROOT = os.path.join(LOCAL_STORAGE_ROOT, "target", "metadata")
    container_name = "metadata"

    # List to collect all test results for the CSV
    csv_results = []

    if os.path.exists(TARGET_ROOT):
        source_items = os.listdir(TARGET_ROOT)
        db_folders = [
            item
            for item in source_items
            if os.path.isdir(os.path.join(TARGET_ROOT, item))
        ]
    else:
        db_folders = []

    if not db_folders:
        print(f"\n[!] Setup Needed: No database metadata folders found inside: {TARGET_ROOT}")
    else:
        print(f"--- Found {len(db_folders)} database profile(s) to process: {db_folders} ---")

        # 3. Iterate through every single database folder found dynamically
        for db_name_target in db_folders:
            print(f" -> [Validating] Comparing local {db_name_target} output against Azure...")

            # Automatically ensure matching target landing directories exist
            target_db_dir = os.path.join(TARGET_ROOT, db_name_target)
            os.makedirs(target_db_dir, exist_ok=True)

            # Check if this specific folder actually contains its required metameta source JSON
            metameta_file = os.path.join(
                TARGET_ROOT, db_name_target, f"{db_name_target}_metameta.json"
            )

            if not os.path.exists(metameta_file):
                print(f" -> [Skip] Missing required schema file: {metameta_file}")
                # Log skipped items to CSV for thorough reporting
                csv_results.append({
                    "Database": db_name_target,
                    "Status": "SKIPPED",
                    "Details": f"Missing local schema file at {metameta_file}",
                    "Added Keys": "",
                    "Removed Keys": "",
                })
                continue

            # Run verification and collect result object
            result = verify_metadata(
                connection_string, db_name_target, container_name, file_name="metameta"
            )
            csv_results.append(result)

        # --- Generate CSV Report ---
        csv_file_path = os.path.join(LOCAL_STORAGE_ROOT, "metadata_verification_report.csv")
        csv_headers = ["Database", "Status", "Details", "Added Keys", "Removed Keys"]

        try:
            with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
                writer.writeheader()
                writer.writerows(csv_results)
            print(f"\n[+] Detailed report successfully generated at: {csv_file_path}")
        except Exception as e:
            logging.error(f"Failed to write CSV file: {e}")
