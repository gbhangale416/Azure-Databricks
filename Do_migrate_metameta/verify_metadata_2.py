import csv
import json
import logging
import os
from azure.storage.blob import BlobClient

# Set up logging to show warnings and errors clearly
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TARGET_ROOT = ""  # Managed dynamically in the main block


def get_remote_json(
    connection_string: str,
    db_name: str,
    container_name: str,
    file_name="metameta",
) -> dict:
    """Fetches remote JSON. Exceptions are handled here to prevent halting the main loop."""
    try:
        if not connection_string:
            raise ValueError("Connection string is empty or invalid.")

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
        logging.error(f"Failed to fetch remote JSON for '{db_name}': {e}")
        return None


def get_local_tgt_metameta(db_name: str):
    """Fetches local JSON. Handles missing files gracefully."""
    path = os.path.join(TARGET_ROOT, db_name, f"{db_name}_metameta.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"Local target metameta file not found at: {path}.")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Local JSON file is corrupted or poorly formatted for '{db_name}': {e}")
        return None


def verify_metadata(
    connection_string: str,
    db_name: str,
    container_name: str,
    file_name="metameta",
) -> dict:
    """Compares local vs remote metadata and safely builds a status dictionary record."""
    # Base structure for our report row
    report_record = {
        "Database": db_name,
        "Status": "PENDING",
        "Details": "",
        "Added Keys": "",
        "Removed Keys": "",
    }

    try:
        remote_json = get_remote_json(
            connection_string, db_name, container_name, file_name
        )
        local_json = get_local_tgt_metameta(db_name)

        if remote_json is None or local_json is None:
            # Pinpoint exactly what was missing
            reasons = []
            if local_json is None: reasons.append("Local config missing/corrupt")
            if remote_json is None: reasons.append("Remote Azure blob missing/failed")
            
            error_msg = f"Verification aborted for '{db_name}': " + " & ".join(reasons)
            logging.error(error_msg)
            
            report_record["Status"] = "ABORTED"
            report_record["Details"] = "; ".join(reasons)
            return report_record

        print("\n" + "=" * 60)
        print(f" METAMETA VERIFICATION REPORT: {db_name.upper()} ")
        print("=" * 60)

        if local_json == remote_json:
            print(f"SUCCESS: Local configuration matches Azure perfectly! For : {db_name.upper()}")
            report_record["Status"] = "SUCCESS"
            report_record["Details"] = "Local configuration matches Azure perfectly."
        else:
            logging.warning(f"MISMATCH DETECTED: Local and remote configurations differ for {db_name}.")
            report_record["Status"] = "MISMATCH"
            report_record["Details"] = "Local and remote configurations differ."

            # Calculate key differences safely
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

    except Exception as e:
        # Catch unexpected runtime quirks during parsing/matching
        logging.error(f"Unexpected internal error running verification on '{db_name}': {e}")
        report_record["Status"] = "FAILED"
        report_record["Details"] = f"Runtime Error: {str(e)}"
        return report_record


if __name__ == "__main__":
    # --- Execution Testing Setup ---
    connection_string = "your_connection_string_here"
    LOCAL_STORAGE_ROOT = os.path.join(os.getcwd(), "mock_storage")
    SOURCE_ROOT = os.path.join(LOCAL_STORAGE_ROOT, "source", "metadata")
    TARGET_ROOT = os.path.join(LOCAL_STORAGE_ROOT, "target", "metadata")
    container_name = "metadata"

    csv_results = []

    if os.path.exists(TARGET_ROOT):
        try:
            source_items = os.listdir(TARGET_ROOT)
            db_folders = [
                item
                for item in source_items
                if os.path.isdir(os.path.join(TARGET_ROOT, item))
            ]
        except Exception as e:
            logging.critical(f"Could not read directory structure at {TARGET_ROOT}: {e}")
            db_folders = []
    else:
        db_folders = []

    if not db_folders:
        print(f"\n[!] Setup Needed: No database metadata folders found inside: {TARGET_ROOT}")
    else:
        print(f"--- Found {len(db_folders)} database profile(s) to process: {db_folders} ---\n")

        # 3. Dynamic Loop Over Databases
        for db_name_target in db_folders:
            # Global try-catch surrounding the core execution loop block
            try:
                print(f" -> [Validating] Comparing local {db_name_target} output against Azure...")

                # Safeguard directory path creation
                target_db_dir = os.path.join(TARGET_ROOT, db_name_target)
                os.makedirs(target_db_dir, exist_ok=True)

                metameta_file = os.path.join(
                    TARGET_ROOT, db_name_target, f"{db_name_target}_metameta.json"
                )

                # Skip gracefully if file isn't present
                if not os.path.exists(metameta_file):
                    print(f" -> [Skip] Missing required schema file: {metameta_file}")
                    csv_results.append({
                        "Database": db_name_target,
                        "Status": "SKIPPED",
                        "Details": f"File '{db_name_target}_metameta.json' missing from target folder.",
                        "Added Keys": "",
                        "Removed Keys": "",
                    })
                    continue  # Continues to the next database profile safely

                # Call validation wrapper
                result = verify_metadata(
                    connection_string, db_name_target, container_name, file_name="metameta"
                )
                csv_results.append(result)

            except Exception as loop_exception:
                # Catch-all safety net for individual iteration failures
                logging.error(f"CRITICAL failure looping over profile '{db_name_target}': {loop_exception}")
                csv_results.append({
                    "Database": db_name_target,
                    "Status": "CRASHED",
                    "Details": f"Loop error: {str(loop_exception)}",
                    "Added Keys": "",
                    "Removed Keys": "",
                })
                continue  # Force continuation of the loop to the next folder

        # --- Generate Final CSV Report ---
        csv_file_path = os.path.join(LOCAL_STORAGE_ROOT, "metadata_verification_report.csv")
        csv_headers = ["Database", "Status", "Details", "Added Keys", "Removed Keys"]

        try:
            # Ensure the output base folder directory exists before saving csv
            os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
            with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
                writer.writeheader()
                writer.writerows(csv_results)
            print(f"[+] Detailed report successfully generated at: {csv_file_path}")
        except Exception as e:
            logging.critical(f"Failed to compile and write final CSV report output: {e}")
