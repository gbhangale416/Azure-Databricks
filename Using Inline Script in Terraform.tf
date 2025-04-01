locals {
  package_config = {
    "package-one"   = null
    "package-two"   = null
    "internal-lib"  = null
    "another-tool"  = null
  }
  trusted_hosts = "--trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org"
}

resource "databricks_cluster" "example_cluster" {
  cluster_name            = "my-databricks-cluster"
  spark_version           = "14.1.x-scala2.12"
  node_type_id            = "Standard_DS3_v2"
  autotermination_minutes = 60
  num_workers             = 2

  init_scripts {
    inline {
      content = <<EOF
#!/bin/bash
${join("\n", [
  for package, _ in local.package_config : "pip install ${local.trusted_hosts} ${package}"
])}
EOF
    }
  }
}
