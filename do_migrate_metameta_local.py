import json
from pathlib import Path


def get_environment_map(
    env_name: str,
    src_metameta: dict,
    global_map_file: str
):
    ret_env_map = {}

    with open(global_map_file, "r") as f:
        g_env_map = json.load(f)

    for meta_key, meta_value in src_metameta.items():

        if not isinstance(meta_value, str):
            continue

        lookup_value = meta_value.lower()

        for section_values in g_env_map.values():

            if not isinstance(section_values, dict):
                continue

            if lookup_value in section_values:

                env_values = section_values[lookup_value]

                if env_name in env_values:
                    ret_env_map[meta_key] = env_values[env_name]
                    break

    return ret_env_map


source_file = (
    "source/metadata/customer/customer_metameta.json"
)

global_map_file = (
    "source/metadata/global_environment_map.json"
)

with open(source_file, "r") as f:
    src_metameta = json.load(f)

env_map = get_environment_map(
    "prd",
    src_metameta,
    global_map_file
)

for key, value in env_map.items():
    src_metameta[key] = value

Path("target").mkdir(
    parents=True,
    exist_ok=True
)

with open(
    "target/customer_metameta.json",
    "w"
) as f:
    json.dump(
        src_metameta,
        f,
        indent=4
    )

print("Completed")


------------------------------------------------------------------------------------------------------------
import json
import os


def get_global_environment_map(source_folder: str):
    with open(
        os.path.join(
            source_folder,
            "metadata",
            "global_environment_map.json"
        ),
        "r"
    ) as f:
        return json.load(f)


def get_environment_map(
    db_name: str,
    account_url: str,  # Not used locally
    container: str,    # Not used locally
    env_name: str,
    src_metameta: dict
):
    ret_env_map = {}

    g_env_map = get_global_environment_map("source")

    for meta_key, meta_value in src_metameta.items():

        if not isinstance(meta_value, str):
            continue

        lookup_value = meta_value.lower()

        for section_values in g_env_map.values():

            if not isinstance(section_values, dict):
                continue

            if lookup_value in section_values:

                env_values = section_values[lookup_value]

                if (
                    isinstance(env_values, dict)
                    and env_name in env_values
                ):
                    ret_env_map[meta_key] = env_values[env_name]
                    break

    return ret_env_map


def get_src_metameta(
    db_name: str,
    account_url: str,
    container: str
):
    file_path = os.path.join(
        "source",
        "metadata",
        db_name,
        f"{db_name}_metameta.json"
    )

    with open(file_path, "r") as f:
        return json.load(f)


def write_metameta_to_destination(
    db_name: str,
    account_url: str,
    metameta_dict: dict,
    container: str
):
    target_dir = os.path.join(
        "target",
        db_name
    )

    os.makedirs(
        target_dir,
        exist_ok=True
    )

    target_file = os.path.join(
        target_dir,
        f"{db_name}_metameta.json"
    )

    with open(target_file, "w") as f:
        json.dump(
            metameta_dict,
            f,
            indent=4
        )


def run_migrate_metameta(
    db_name: str,
    env_name: str
):

    src_metameta = get_src_metameta(
        db_name,
        None,
        None
    )

    env_map = get_environment_map(
        db_name,
        None,
        None,
        env_name,
        src_metameta
    )

    # Generic replacement
    for key, value in env_map.items():
        src_metameta[key] = value

    write_metameta_to_destination(
        db_name,
        None,
        src_metameta,
        None
    )

    print(
        f"Completed migration for {db_name}"
    )


if __name__ == "__main__":

    run_migrate_metameta(
        db_name="customer",
        env_name="prd"
    )
