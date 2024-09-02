import requests
import os

def get_changed_sql_scripts():
    # Azure DevOps organization and project details
    organization = os.environ["AZURE_DEVOPS_ORG"]
    project = os.environ["AZURE_DEVOPS_PROJECT"]
    pipeline_id = os.environ["AZURE_DEVOPS_PIPELINE_ID"]
    
    # Azure DevOps Personal Access Token (PAT)
    pat = os.environ["AZURE_DEVOPS_PAT"]

    # Prepare the API request to get the last successful build
    url = f"https://dev.azure.com/{organization}/{project}/_apis/build/builds?definitions={pipeline_id}&statusFilter=completed&resultFilter=succeeded&$top=1&api-version=7.1-preview.1"
    response = requests.get(url, auth=('', pat))
    last_successful_build = response.json()["value"][0]
    last_successful_commit = last_successful_build["sourceVersion"]

    # Prepare the API request to get the changed files since the last successful build
    changes_url = f"https://dev.azure.com/{organization}/{project}/_apis/build/builds/{last_successful_build['id']}/changes?api-version=7.1-preview.1"
    changes_response = requests.get(changes_url, auth=('', pat))
    changes = changes_response.json()["value"]

    # Filter the changed files to include only SQL scripts
    changed_scripts = [change["item"]["path"] for change in changes if change["item"]["path"].endswith(".sql")]

    # Write the changed SQL scripts to a file
    with open("changed_scripts.txt", "w") as file:
        for script in changed_scripts:
            file.write(f"{script}\n")

if __name__ == "__main__":
    get_changed_sql_scripts()
