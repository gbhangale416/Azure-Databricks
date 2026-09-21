terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }

    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "databricks" {
  host = var.databricks_host

  azure_workspace_resource_id = var.databricks_workspace_resource_id
}


# ---------------------------------------------------------
# Existing Azure Key Vault secret
# ---------------------------------------------------------

data "azurerm_key_vault_secret" "snowflake_private_key" {

  name         = var.snowflake_private_key_secret_name
  key_vault_id = var.key_vault_id
}


# ---------------------------------------------------------
# Convert PEM into Databricks single-line format
# ---------------------------------------------------------

locals {

  snowflake_pem_private_key = trimspace(
    replace(
      replace(
        replace(
          replace(
            data.azurerm_key_vault_secret.snowflake_private_key.value,
            "-----BEGIN PRIVATE KEY-----",
            ""
          ),
          "-----END PRIVATE KEY-----",
          ""
        ),
        "\r",
        ""
      ),
      "\n",
      ""
    )
  )
}


# ---------------------------------------------------------
# Databricks Unity Catalog Snowflake Connection
# ---------------------------------------------------------

resource "databricks_connection" "snowflake" {

  name = var.connection_name

  connection_type = "SNOWFLAKE"

  comment = "Snowflake connection using PEM private key"

  options = {

    host = var.snowflake_host

    port = "443"

    user = var.snowflake_user

    sfWarehouse = var.snowflake_warehouse

    pem_private_key = local.snowflake_pem_private_key

    expires_in_secs = tostring(var.expires_in_secs)

    # Optional
    # sfRole = var.snowflake_role
  }
}


# ---------------------------------------------------------
# Variables
# ---------------------------------------------------------

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

variable "snowflake_role" {
  type    = string
  default = null
}

variable "connection_name" {
  type = string
}

variable "expires_in_secs" {
  type    = number
  default = 3600
}
