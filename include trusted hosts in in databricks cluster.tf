locals {
  packages = [
    "package-one",
    "package-two",
    "internal-lib",
    "another-tool"
  ]
  trusted_hosts = "--trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org"
}

# Upload the init script to DBFS
resource "databricks_dbfs_file" "init_script" {
  destination = "dbfs:/databricks/scripts/init-script.sh"

  content_base64 = base64encode(<<EOT
#!/bin/bash
# Add trusted hosts to pip configuration
mkdir -p /databricks/scripts/
echo "[global]" > /databricks/scripts/pip.conf
echo "trusted-host = pypi.org" >> /databricks/scripts/pip.conf
echo "trusted-host = files.pythonhosted.org" >> /databricks/scripts/pip.conf

# Loop through all packages and install them with trusted hosts
$(join("\n", [
  for package in local.packages : "pip install ${local.trusted_hosts} ${package}"
]))
EOT
  )
}

# Create the Databricks Cluster
resource "databricks_cluster" "example_cluster" {
  cluster_name            = "my-databricks-cluster"
  spark_version           = "14.1.x-scala2.12"
  node_type_id            = "Standard_DS3_v2"
  autotermination_minutes = 60
  num_workers             = 2

  # Attach the init script from DBFS
  init_scripts {
    dbfs {
      destination = databricks_dbfs_file.init_script.destination
    }
  }
}
include trusted hosts in
