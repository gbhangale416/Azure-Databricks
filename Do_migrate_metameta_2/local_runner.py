import json
import logging
import os

# Set up clean logging configuration
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --- Local Directory Root Setup ---
LOCAL_STORAGE_ROOT = os.path.join(os.getcwd(), "mock_storage")
SOURCE_ROOT = os.path.join(LOCAL_STORAGE_ROOT, "source", "metadata")
TARGET_ROOT = os.path.join(LOCAL_STORAGE_ROOT, "target", "metadata")


# -----------------------------------------------------------------
# EXTRACTED SPECIAL CONDITION FUNCTIONS
# -----------------------------------------------------------------

def handle_special_destination_database(src_metameta, g_env_map, env_name):
    """
    SPECIAL CONDITION: Checks source_type exclusions and forces uppercase.
    """
    dest_db_val = src_metameta['destination_database']
    rt_dest_db = dest_db_val

    if (
        'source_type' not in src_metameta or
        src_metameta['source_type'].lower() != 'snowflake'
    ):
        database_mapping = g_env_map.get("Database", {})
        if dest_db_val.lower() in database_mapping:
            rt_dest_db = database_mapping[dest_db_val.lower()][env_name]
            rt_dest_db = rt_dest_db.upper()

    return rt_dest_db


def handle_special_destination_warehouse(src_metameta, g_env_map, env_name):
    """
    SPECIAL CONDITION: Switches mapping block context based on destination_type value.
    """
    dest_wh_val = src_metameta['destination_warehouse']
    rt_dest_wh = dest_wh_val

    if (
        'destination_type' in src_metameta and
        src_metameta['destination_type'].lower() == "sql server"
    ):
        server_mapping = g_env_map.get("Server", {})
        if dest_wh_val.lower() in server_mapping:
            rt_dest_wh = server_mapping[dest_wh_val.lower()][env_name]
    else:
        warehouse_mapping = g_env_map.get("Warehouse", {})
        if dest_wh_val.lower() in warehouse_mapping:
            rt_dest_wh = warehouse_mapping[dest_wh_val.lower()][env_name]
            rt_dest_wh = rt_dest_wh.upper()

    return rt_dest_wh


def handle_special_source_database(src_metameta, g_env_map, env_name):
    """
    SPECIAL CONDITION: Diverges mapping behavior between Snowflake vs SQLDatabase structural blocks.
    """
    src_db_val = src_metameta['source_database']
    rt_src_db = src_db_val

    if (
        'source_type' in src_metameta and
        src_metameta['source_type'].lower() == "snowflake"
    ):
        database_mapping = g_env_map.get("Database", {})
        if src_db_val.lower() in database_mapping:
            rt_src_db = database_mapping[src_db_val.lower()][env_name]
            rt_src_db = rt_src_db.upper()
    else:
        sql_db_mapping = g_env_map.get("SQLDatabase", {})
        if src_db_val.lower() in sql_db_mapping:
            rt_src_db = sql_db_mapping[src_db_val.lower()][env_name]

    return rt_src_db


def handle_special_archive_database(src_metameta, g_env_map, env_name):
    """
    SPECIAL CONDITION: Evaluates archive databases using Snowflake conditional exclusions.
    """
    archive_db_val = src_metameta['archive_database']
    rt_archive_db = archive_db_val

    if (
        'source_type' not in src_metameta or
        src_metameta['source_type'].lower() != "snowflake"
    ):
        database_mapping = g_env_map.get("Database", {})
        if archive_db_val.lower() in database_mapping:
            rt_archive_db = database_mapping[archive_db_val.lower()][env_name]
            rt_archive_db = rt_archive_db.upper()

    return rt_archive_db


def replace_db_in_procedurename_per_env(procedure_name, database_mapping, env_name):
    """
    SPECIAL CONDITION: Modifies the target string name format for post-execution procedures.
    """
    val_str = str(procedure_name)
    for db_key, env_dict in database_mapping.items():
        if db_key in val_str.lower() and env_name in env_dict:
            return val_str.replace(db_key, env_dict[env_name])
    return val_str


# -----------------------------------------------------------------
# ENGINE STANDARD PREFERENCE LOOKUP UTILITY
# -----------------------------------------------------------------

def handle_standard_lookup(key, value, target_env, db_name, g_env_map, lookup_table):
    """
    STANDARD FALLBACK ENGINE (NON-SPECIAL KEYS):
    Evaluates tier preferences (Database compound match -> Category match -> Global match).
    """
    val_str = str(value)
    
    if key in g_env_map and isinstance(g_env_map[key], dict):
        category_map = g_env_map[key]
        
        bracket_key = f"[{db_name}][{val_str}]"
        if bracket_key in category_map:
            if target_env in category_map[bracket_key]:
                return category_map[bracket_key][target_env]
                
        if val_str in category_map:
            if target_env in category_map[val_str]:
                return category_map[val_str][target_env]

    if val_str in lookup_table:
        matched_block = lookup_table[val_str]
        if target_env in matched_block:
            return matched_block[target_env]
            
    elif val_str.endswith('_nt1'):
        cleaned_val = val_str[:-4]
        if cleaned_val in lookup_table:
            matched_block = lookup_table[cleaned_val]
            if target_env in matched_block:
                return matched_block[target_env]
                
    return value


# -----------------------------------------------------------------
# CORE ROOT-LEVEL PROCESSING ENGINE (NON-RECURSIVE)
# -----------------------------------------------------------------

def update_metadata_values(config_node, target_env, db_name, g_env_map, lookup_table):
    """
    NON-RECURSIVE: Processes root configuration settings key-by-key flatly.
    Executes specialized helper conditionals when matching targeted override fields.
    """
    if not isinstance(config_node, dict):
        return

    for key in list(config_node.keys()):
        value = config_node[key]
        
        # 1. Skip entities section completely
        if key == "entities":
            logging.info("--> Skipping 'entities' section during global metadata update.")
            continue
        
        # 2. ENGAGE SPECIAL CONDITIONAL EVALUATIONS
        if key == "destination_database":
            config_node[key] = handle_special_destination_database(config_node, g_env_map, target_env)
            logging.info(f"[Special Condition] '{key}' -> '{config_node[key]}'")
            continue
            
        elif key == "destination_warehouse":
            config_node[key] = handle_special_destination_warehouse(config_node, g_env_map, target_env)
            logging.info(f"[Special Condition] '{key}' -> '{config_node[key]}'")
            continue
            
        elif key == "source_database":
            config_node[key] = handle_special_source_database(config_node, g_env_map, target_env)
            logging.info(f"[Special Condition] '{key}' -> '{config_node[key]}'")
            continue
            
        elif key == "archive_database":
            config_node[key] = handle_special_archive_database(config_node, g_env_map, target_env)
            logging.info(f"[Special Condition] '{key}' -> '{config_node[key]}'")
            continue
            
        elif key == "post_execution_procedure":
            db_mapping = g_env_map.get("Database", {})
            config_node[key] = replace_db_in_procedurename_per_env(value, db_mapping, target_env)
            logging.info(f"[Special Condition] '{key}' -> '{config_node[key]}'")
            continue

        # 3. STANDARD KEY PREFERENCE MAPPING FALLBACK
        if isinstance(value, str):
            new_value = handle_standard_lookup(key, value, target_env, db_name, g_env_map, lookup_table)
            if new_value != value:
                config_node[key] = new_value
                logging.info(f"[Standard Processed] '{key}' | Old: '{value}' -> New: '{new_value}'")


def update_entities_only(entities_node, target_env, db_name, g_env_map, lookup_table):
    """
    SEPARATE FUNCTION (NON-RECURSIVE): Processes values inside the entities block level flatly.
    """
    if isinstance(entities_node, list):
        for item in entities_node:
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, str):
                        new_value = handle_standard_lookup(key, value, target_env, db_name, g_env_map, lookup_table)
                        if new_value != value:
                            item[key] = new_value
                            logging.info(f"[Entity Update] Swapped -> Key: '{key}' | Old: '{value}' -> New: '{new_value}'")
                            
    elif isinstance(entities_node, dict):
        for key, value in entities_node.items():
            if isinstance(value, str):
                new_value = handle_standard_lookup(key, value, target_env, db_name, g_env_map, lookup_table)
                if new_value != value:
                    entities_node[key] = new_value
                    logging.info(f"[Entity Update] Swapped -> Key: '{key}' | Old: '{value}' -> New: '{new_value}'")


# -----------------------------------------------------------------
# MASTER MAPPING SYSTEM SETUP
# -----------------------------------------------------------------

def auto_discover_env_keys(data_block, discovered_keys=None):
    if discovered_keys is None:
        discovered_keys = set()
    if isinstance(data_block, dict):
        if data_block and all(isinstance(v, str) for v in data_block.values()):
            for k in data_block.keys():
                discovered_keys.add(str(k))
        else:
            for value in data_block.values():
                auto_discover_env_keys(value, discovered_keys)
    return discovered_keys


def extract_mappings(data_block, env_keys_set, lookup_table):
    if isinstance(data_block, dict):
        if env_keys_set.issubset(data_block.keys()) or any(k in data_block for k in env_keys_set):
            return data_block
        for key, value in data_block.items():
            res = extract_mappings(value, env_keys_set, lookup_table)
            if res:
                lookup_table[key] = res
                for env_val in res.values():
                    if isinstance(env_val, str):
                        lookup_table[env_val] = res
    return None


def get_environment_map(db_name: str, src_env: str, src_container: str, env_name: str, src_metameta: dict):
    global_map_file = os.path.join(SOURCE_ROOT, "global_environment_map.json")
    if not os.path.exists(global_map_file):
        logging.error(f"Global environment map missing during transformation at: {global_map_file}")
        return src_metameta

    with open(global_map_file, 'r') as f:
        g_env_map = json.load(f)

    env_keys_set = auto_discover_env_keys(g_env_map)
    lookup_table = {}
    extract_mappings(g_env_map, env_keys_set, lookup_table)

    working_meta = json.loads(json.dumps(src_metameta))
    update_metadata_values(working_meta, env_name, db_name, g_env_map, lookup_table)
    return working_meta


# -----------------------------------------------------------------
# MOCK STORAGE IO LAYER
# -----------------------------------------------------------------

def get_src_metameta(db_name: str, *args):
    path = os.path.join(SOURCE_ROOT, db_name, f"{db_name}_metameta.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Local source metameta file not found at: {path}")
        return None


def get_tgt_metameta(db_name: str, *args):
    path = os.path.join(TARGET_ROOT, db_name, f"{db_name}_metameta.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"Local target metameta file not found at: {path}. Assuming fresh run.")
        return None


def write_metameta_to_destination(db_name: str, account_url: str, metameta_dict: dict, container: str):
    target_dir = os.path.join(TARGET_ROOT, db_name)
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, f"{db_name}_metameta.json")
    with open(path, 'w') as f:
        json.dump(metameta_dict, f, indent=2)
    logging.info(f"Local file cleanly written to: {path}")


def run_migrate_metameta(db_name: str, src_env: str, tgt_env: str, src_container: str, tgt_container: str, env_name: str):
    src_metameta = get_src_metameta(db_name, src_env, src_container)
    if not src_metameta:
        return
    mapped_meta = get_environment_map(db_name, src_env, src_container, env_name, src_metameta)
    write_metameta_to_destination(db_name, tgt_env, mapped_meta, tgt_container)


# -----------------------------------------------------------------
# EXECUTION ENTRY
# -----------------------------------------------------------------
if __name__ == "__main__":
    print(">>> Beginning dynamic local emulation framework run...")
    
    local_execution_parameters = {
        "src_container": "local-src-container",
        "tgt_container": "local-tgt-container",
        "env_name": "prd"
    }
    
    global_map_file = os.path.join(SOURCE_ROOT, "global_environment_map.json")
    
    if not os.path.exists(global_map_file):
        print(f"\n[!] Setup Needed: Global Environment Map file is missing at {global_map_file}")
    else:
        if os.path.exists(SOURCE_ROOT):
            source_items = os.listdir(SOURCE_ROOT)
            db_folders = [item for item in source_items if os.path.isdir(os.path.join(SOURCE_ROOT, item))]
        else:
            db_folders = []

        if not db_folders:
            print(f"\n[!] Setup Needed: No database metadata folders found inside: {SOURCE_ROOT}")
        else:
            print(f"--- Detected {len(db_folders)} database profile(s) to process: {db_folders} ---")
            for db_name_target in db_folders:
                print(f"\n[Loop Execution] Starting mapping sequence for schema: '{db_name_target}'")
                metameta_file = os.path.join(SOURCE_ROOT, db_name_target, f"{db_name_target}_metameta.json")
                if not os.path.exists(metameta_file):
                    continue
                
                run_migrate_metameta(
                    db_name_target,
                    "local_src", "local_tgt",
                    local_execution_parameters["src_container"],
                    local_execution_parameters["tgt_container"],
                    local_execution_parameters["env_name"]
                )
            print("\n>>> All discovered folder transformation loops safely completed.")
