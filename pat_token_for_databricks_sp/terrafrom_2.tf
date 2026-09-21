terraform {
  required_version = ">= 1.5.0"

  required_providers {

    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.49"
    }

    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.0"
    }
  }
}


# ==========================================================
# PROVIDERS
# ==========================================================

provider "azurerm" {

  features {}
}


provider "databricks" {

  host = var.databricks_host

  azure_workspace_resource_id = var.databricks_workspace_resource_id
}


# ==========================================================
# EXISTING AZURE KEY VAULT SECRET
# ==========================================================

data "azurerm_key_vault_secret" "snowflake_private_key" {

  name = var.snowflake_private_key_secret_name

  key_vault_id = var.key_vault_id
}


# ==========================================================
# PEM PROCESSING
# ==========================================================

locals {

  # Original PEM
  snowflake_private_key_pem = data.azurerm_key_vault_secret.snowflake_private_key.value


  # Extract body between BEGIN and END.
  #
  # Supports:
  #
  # BEGIN PRIVATE KEY
  # BEGIN RSA PRIVATE KEY
  # BEGIN ENCRYPTED PRIVATE KEY
  #
  snowflake_private_key_body = regex(
    "-----BEGIN [^-]+-----([\\s\\S]*?)-----END [^-]+-----",
    local.snowflake_private_key_pem
  )[0]


  # Remove all whitespace/newlines.
  #
  # PEM:
  #
  # MIIEvQIB
  # ADANBgkqh
  # kiG9w0...
  #
  # Result:
  #
  # MIIEvQIBADANBgkqhkiG9w0...
  #
  snowflake_private_key = join(
    "",
    regexall(
      "[A-Za-z0-9+/=]+",
      local.snowflake_private_key_body
    )
  )
}


# ==========================================================
# DATABRICKS UNITY CATALOG CONNECTION
# ==========================================================

resource "databricks_connection" "snowflake" {

  name = var.connection_name

  connection_type = "SNOWFLAKE"

  comment = "Snowflake PEM authentication"


  options = {

    host = var.snowflake_host

    port = "443"

    user = var.snowflake_user

    sfWarehouse = var.snowflake_warehouse

    pem_private_key = local.snowflake_private_key

    expires_in_secs = tostring(var.expires_in_secs)
  }
}


# ==========================================================
# OUTPUT
# ==========================================================

output "snowflake_connection_name" {

  value = databricks_connection.snowflake.name
}


# ==========================================================
# VARIABLES
# ==========================================================

variable "databricks_host" {

  type = string
}


variable "databricks_workspace_resource_id" {

  type = string
}


variable "key_vault_id" {

  type = string
}


variable "snowflake_private_key_secret_name" {

  type = string
}


variable "snowflake_host" {

  type = string
}


variable "snowflake_user" {

  type = string
}


variable "snowflake_warehouse" {

  type = string
}


variable "connection_name" {

  type = string
}


variable "expires_in_secs" {

  type    = number
  default = 3600
}
