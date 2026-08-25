import os
from typing import Callable, Iterable, Optional

def process_bundle_files(
    base_path: str,
    file_transformer: Callable[[str, str], Optional[str]],
    target_folder_name: Optional[str] = None,   # e.g., 'jobs', 'notebooks', 'sql'
    file_extensions: Optional[Iterable[str]] = (".yml", ".yaml"),
    skip_dirs: Optional[Iterable[str]] = ("__pycache__", ".git", "utils")
) -> None:
    """
    Recursively scans base_path across all data_product subdirectories.
    """
    if not os.path.exists(base_path):
        print(f"Error: Base path '{base_path}' does not exist.")
        return

    for root, dirs, files in os.walk(base_path):
        # Exclude internal/cache folders
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        # If a target subfolder (e.g., 'jobs') is specified, only process if inside it
        if target_folder_name:
            folder_parts = [p.lower() for p in os.path.normpath(root).split(os.sep)]
            if target_folder_name.lower() not in folder_parts:
                continue

        for file in files:
            if file_extensions and not any(file.endswith(ext) for ext in file_extensions):
                continue

            full_path = os.path.join(root, file)
            print(f"Processing file: {full_path}")
            
            try:
                with open(full_path, "r", encoding="utf-8") as rf:
                    original = rf.read()

                updated = file_transformer(original, full_path)

                if updated is not None and updated != original:
                    with open(full_path, "w", encoding="utf-8") as wf:
                        wf.write(updated)
            except Exception as e:
                print(f"Error processing {full_path}: {e}")
