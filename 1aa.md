You can run this command locally from the **VS Code terminal** using Azure CLI (`az`) and `jq`.

One important change is required: `$(CURRENT_BRANCH_NAME)` is an Azure DevOps pipeline variable. Locally, you need to define it as a shell variable or replace it with your actual Git branch name.

## **1. Prerequisites**

Open VS Code terminal and check:

```
az --version
git --version
jq --version
```

If Azure CLI is not installed, install it from the official [Azure CLI installation guide](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli?utm_source=chatgpt.com).

Install the Azure DevOps extension:

```
az extension add --name azure-devops
```

## **2. Login to Azure DevOps**

```
az login
```

Configure your Azure DevOps organization and project:

```
az devops configure --defaults organization=https://dev.azure.com/<organization-name> project=<project-name>
```

Replace the placeholders with your actual organization and project.

## **3. Run the command locally (VS Code)**

### **Option A: Git Bash / Linux / macOS terminal**

First, get your current Git branch:

```
export CURRENT_BRANCH_NAME=$(git branch --show-current)

echo $CURRENT_BRANCH_NAME
```

Now run the updated command:

```
export LAST_SUCCESSFUL_BUILD_COMMIT=$(az pipelines build list \
    --branch "$CURRENT_BRANCH_NAME" \
    --top 100 \
    -o json | jq -r '
        [.[] |
        select(.buildNumber | startswith("dept_edi_pipeline_")) |
        select(.result == "succeeded")] |
        .[0].sourceVersion
    ')

echo "Last successful build commit: $LAST_SUCCESSFUL_BUILD_COMMIT"
```

### **Option B: PowerShell terminal (Windows)**

```
$builds = az pipelines build list `
    --branch master `
    --top 100 `
    --output json | ConvertFrom-Json

$LAST_SUCCESSFUL_BUILD_COMMIT = $builds |
    Where-Object {
        $_.buildNumber -like "dept_edi_pipeline_*" -and
        $_.result -eq "succeeded"
    } |
    Sort-Object finishTime -Descending |
    Select-Object -First 1 -ExpandProperty sourceVersion

Write-Host "LAST_SUCCESSFUL_BUILD_COMMIT: $LAST_SUCCESSFUL_BUILD_COMMIT"

Write-Host "Last successful build commit: $LAST_SUCCESSFUL_BUILD_COMMIT"
```

## **4. Verify the output**

Run:

```
echo $LAST_SUCCESSFUL_BUILD_COMMIT
```

It should return a Git commit SHA, for example:

```
a1b2c3d4e5f6789012345678901234567890abcd
```

## **5. Important: Configure Azure DevOps**

If you get an error about the default organization or project, run:

```
az devops configure --defaults \
    organization=https://dev.azure.com/<organization-name> \
    project=<project-name>
```

If you get a permissions error, verify that your logged-in Azure DevOps user has permission to view pipeline builds.

**Note:** I also corrected the `jq` expression from your screenshot. The original expression outputs individual objects before trying to access `[0]`. The updated expression first creates an array and then selects the first successful build's commit.

This gives you the local equivalent of the Azure DevOps pipeline variable `LAST_SUCCESSFUL_BUILD_COMMIT`.
