import os

# -------------------------------------------------------------------------
# Dynamic credential resolution based on target environment
# -------------------------------------------------------------------------
# Assumes the environment is passed either via argument (e.g., args.db_env)
# or via an environment variable TARGET_ENVIRONMENT.
db_env = str(args.db_env if hasattr(args, "db_env") else os.environ.get("TARGET_ENVIRONMENT", "")).lower()

if db_env in ["dev", "tst", "dev_test"]:
    if "SF_PASSWORD_DEV_TEST" not in os.environ:
        raise ValueError("The SF_PASSWORD_DEV_TEST environment variable has not been defined")
    if "SF_PRIVATE_KEY_DEV_TEST" not in os.environ:
        raise ValueError("The SF_PRIVATE_KEY_DEV_TEST environment variable has not been defined")
    
    # Map them to the standard variables expected by the connector/snowdeploy
    os.environ["SNOWSQL_PWD"] = os.environ["SF_PASSWORD_DEV_TEST"]
    os.environ["SF_PRIVATE_KEY"] = os.environ["SF_PRIVATE_KEY_DEV_TEST"]

elif db_env in ["prd", "prod", "preprod", "uat"]:
    if "SF_PASSWORD" not in os.environ:
        raise ValueError("The SF_PASSWORD environment variable has not been defined")
    if "SF_PRIVATE_KEY" not in os.environ:
        raise ValueError("The SF_PRIVATE_KEY environment variable has not been defined")
    
    # Map them to the standard variables expected by the connector/snowdeploy
    os.environ["SNOWSQL_PWD"] = os.environ["SF_PASSWORD"]
    # os.environ["SF_PRIVATE_KEY"] is already populated

else:
    raise ValueError(f"Unrecognized or missing target environment: '{db_env}'")

# Root folder validation (unchanged)
root_folder = os.path.abspath(root_folder)
if not os.path.isdir(root_folder):
    raise ValueError("Invalid root folder: %s" % root_folder)
