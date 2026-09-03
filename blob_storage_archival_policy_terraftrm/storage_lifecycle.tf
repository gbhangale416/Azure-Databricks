resource "azurerm_storage_management_policy" "extract" {
  storage_account_id = azurerm_storage_account.storage.id

  rule {
    name    = "extract-retention"
    enabled = true

    filters {
      prefix_match = ["extract/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        # DEV / TEST
        # Delete blobs after 7 days
        delete_after_days_since_modification_greater_than = contains(
          ["dev", "test"],
          lower(var.RESOURCE_NAMING_PREFIX)
        ) ? 7 : null

        # PROD
        # Move blobs to Archive after 730 days
        tier_to_archive_after_days_since_modification_greater_than = (
          lower(var.RESOURCE_NAMING_PREFIX) == "prod"
          ? 730
          : null
        )
      }
    }
  }
}
