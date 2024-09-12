import os

def run_files_in_path(relative_path):
    # Get the absolute path based on the relative path
    base_path = os.path.abspath(relative_path)
    
    # Walk through all folders and subfolders
    for root, dirs, files in os.walk(base_path):
        for file in files:
            # Check if the file is a Python file
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                print(f"Running file: {full_path}")
                try:
                    # Use the %run magic command to run the file
                    dbutils.notebook.run(full_path, timeout_seconds=600)
                except Exception as e:
                    print(f"Error running file {full_path}: {e}")

# Example usage: pass the relative path to run files in a folder
relative_path = './my-folder/'
run_files_in_path(relative_path)
