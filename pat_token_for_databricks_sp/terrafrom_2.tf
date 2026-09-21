data "azurerm_key_vault_secret" "snowflake_private_key" {
  name         = var.snowflake_private_key_secret_name
  key_vault_id = var.key_vault_id
}

locals {
  snowflake_private_key = regexreplace(
    data.azurerm_key_vault_secret.snowflake_private_key.value,
    "-----BEGIN [^-]+-----|-----END [^-]+-----|\\s+",
    ""
  )
}

resource "databricks_connection" "snowflake" {
  name            = var.connection_name
  connection_type = "SNOWFLAKE"

  options = {
    host            = var.snowflake_host
    port            = "443"
    user            = var.snowflake_user
    sfWarehouse     = var.snowflake_warehouse
    pem_private_key = local.snowflake_private_key
    expires_in_secs = tostring(var.expires_in_secs)
  }
}
