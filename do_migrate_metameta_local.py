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


--------------------------------------------------------------------------------------------------------------------------------------------------
import json
import os
from pathlib import Path


SOURCE_FOLDER = "source"
TARGET_FOLDER = "target"


def load_global_environment_map():
    with open(
        os.path.join(
            SOURCE_FOLDER,
            "metadata",
            "global_environment_map.json"
        ),
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def replace_values(obj, global_env_map, env_name):

    if isinstance(obj, dict):
        return {
            k: replace_values(v, global_env_map, env_name)
            for k, v in obj.items()
        }

    elif isinstance(obj, list):
        return [
            replace_values(item, global_env_map, env_name)
            for item in obj
        ]

    elif isinstance(obj, str):

        lookup_value = obj.lower()

        for section_values in global_env_map.values():

            if not isinstance(section_values, dict):
                continue

            if lookup_value in section_values:

                env_values = section_values[lookup_value]

                if (
                    isinstance(env_values, dict)
                    and env_name in env_values
                ):
                    return env_values[env_name]

        return obj

    return obj


def run_migrate_metameta(
    db_name: str,
    env_name: str
):

    source_file = os.path.join(
        SOURCE_FOLDER,
        db_name,
        f"{db_name}_metameta.json"
    )

    target_file = os.path.join(
        TARGET_FOLDER,
        db_name,
        f"{db_name}_metameta.json"
    )

    with open(
        source_file,
        "r",
        encoding="utf-8"
    ) as f:
        src_metameta = json.load(f)

    global_env_map = load_global_environment_map()

    updated_json = replace_values(
        src_metameta,
        global_env_map,
        env_name
    )

    Path(
        os.path.dirname(target_file)
    ).mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        target_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            updated_json,
            f,
            indent=4
        )

    print(
        f"Completed migration for {db_name}"
    )
    print(
        f"Output written to {target_file}"
    )


if __name__ == "__main__":

    run_migrate_metameta(
        db_name="ACG_Lag",
        env_name="prd"
    )


##############################################################################################################################
import json
import os
from pathlib import Path


SOURCE_FOLDER = "source"
TARGET_FOLDER = "target"
ENV_NAME = "prd"  # dev, tst, uat, prd


def load_global_environment_map():
    env_map_file = os.path.join(
        SOURCE_FOLDER,
        "metadata",
        "global_environment_map.json"
    )

    with open(env_map_file, "r", encoding="utf-8") as f:
        return json.load(f)


def replace_values(obj, global_env_map, env_name):
    """
    Recursively traverse JSON and replace values
    using global_environment_map.json
    """

    if isinstance(obj, dict):

        for key, value in obj.items():
            obj[key] = replace_values(
                value,
                global_env_map,
                env_name
            )

        return obj

    elif isinstance(obj, list):

        return [
            replace_values(
                item,
                global_env_map,
                env_name
            )
            for item in obj
        ]

    elif isinstance(obj, str):

        lookup_value = obj.lower()

        for section_name, section_values in global_env_map.items():

            if not isinstance(section_values, dict):
                continue

            if lookup_value in section_values:

                env_values = section_values[lookup_value]

                if (
                    isinstance(env_values, dict)
                    and env_name in env_values
                ):
                    print(
                        f"Replacing '{obj}' "
                        f"with '{env_values[env_name]}'"
                    )

                    return env_values[env_name]

        return obj

    return obj


def process_file(file_path, global_env_map):

    with open(file_path, "r", encoding="utf-8") as f:
        source_json = json.load(f)

    updated_json = replace_values(
        source_json,
        global_env_map,
        ENV_NAME
    )

    relative_path = os.path.relpath(
        file_path,
        SOURCE_FOLDER
    )

    target_file = os.path.join(
        TARGET_FOLDER,
        relative_path
    )

    Path(
        os.path.dirname(target_file)
    ).mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        target_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            updated_json,
            f,
            indent=4
        )

    print(f"Written: {target_file}")


def process_all_files():

    global_env_map = load_global_environment_map()

    for root, dirs, files in os.walk(SOURCE_FOLDER):

        for file_name in files:

            if file_name == "global_environment_map.json":
                continue

            if file_name.endswith(".json"):

                file_path = os.path.join(
                    root,
                    file_name
                )

                print(
                    f"\nProcessing: {file_path}"
                )

                process_file(
                    file_path,
                    global_env_map
                )


if __name__ == "__main__":

    process_all_files()

    print("\nCompleted Successfully")
