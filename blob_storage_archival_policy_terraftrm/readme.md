## ServiceNow Story: Azure Blob Storage – Extract Container Archival

**Title:**
Implement Azure Blob Storage Lifecycle Policy for Extract Container

**Description:**
Configure an Azure Storage Lifecycle Management policy for the `extract` container to automatically manage data retention based on the deployment environment.

The lifecycle policy should be implemented as a single Terraform policy and use `var.RESOURCE_NAMING_PREFIX` to determine the appropriate action for each environment.

### Requirements

| Environment | Container | Action               | Retention      |
| ----------- | --------- | -------------------- | -------------- |
| DEV         | `extract` | Delete               | After 7 days   |
| TEST        | `extract` | Delete               | After 7 days   |
| PROD        | `extract` | Move to Archive tier | After 730 days |
| PROD        | `extract` | Delete               | Never          |

The lifecycle policy must apply to **all block blobs within the `extract` container**, regardless of virtual folder/depth.

Example:

```text
extract/
├── file.csv
├── 2026/file.csv
├── 2026/09/file.csv
└── department/team/2026/file.csv
```

The policy should apply to all of the above files.

### Terraform Implementation

Use `var.RESOURCE_NAMING_PREFIX` to determine the environment-specific action:

```hcl
actions {
  base_blob {
    delete_after_days_since_modification_greater_than = (
      contains(["dev", "test"], var.RESOURCE_NAMING_PREFIX) ? 7 : null
    )

    tier_to_archive_after_days_since_modification_greater_than = (
      var.RESOURCE_NAMING_PREFIX == "prod" ? 730 : null
    )
  }
}
```

### Acceptance Criteria

* [ ] A single Azure Storage Lifecycle Management policy is implemented using Terraform.
* [ ] The policy targets the `extract` container.
* [ ] DEV blobs are automatically deleted after 7 days.
* [ ] TEST blobs are automatically deleted after 7 days.
* [ ] PROD blobs are moved to the Archive tier after 730 days.
* [ ] PROD blobs are **not automatically deleted**.
* [ ] The policy applies to blobs at any virtual folder depth under `extract`.
* [ ] Environment selection is based on `var.RESOURCE_NAMING_PREFIX`.
* [ ] Existing storage account and container configuration remains unchanged.
* [ ] Terraform plan/apply completes successfully for DEV, TEST, and PROD.
* [ ] The lifecycle configuration is validated after deployment.

### Out of Scope

* Manual deletion of existing blobs.
* Manual movement of blobs to the Archive tier.
* Changes to storage account/container creation.
* Changes to application upload processes.
* Deletion of PROD archived data.

**Expected Outcome:**
Data in the `extract` container is automatically managed according to the environment-specific retention requirements, reducing unnecessary storage usage in DEV/TEST while retaining PROD data in the Azure Archive tier.
