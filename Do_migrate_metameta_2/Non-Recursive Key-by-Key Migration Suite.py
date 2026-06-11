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
# DYNAMIC ENVIRONMENT TRACKING ENGINE (NON-RECURSIVE)
# -----------------------------------------------------------------

def auto_discover_env_keys(data_block, discovered_keys=None):
    """
    Scans the environment map to automatically discover environment keys (e.g., dev, tst, uat, prd)
    without hardcoding them. It looks for leaf dictionary objects where values are strings.
    """
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
    """
    Recursively builds the lookup table from the global environment map using discovered keys.
    """
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


def handle_special_destination_database(src_metameta, g_env_map, env_name):
    """
    SPECIAL CONDITION FUNCTION:
    Evaluates destination_database rules explicitly when matched during key-by-key processing.
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


def handle_standard_lookup(key, value, target_env, db_name, g_env_map, lookup_table):
    """
    STANDARD FALLBACK FUNCTION (GENERIC ACROSS ALL KEYS):
    Evaluates replacements using a strict multi-tier preference hierarchy:
    1. Highest Preference: Specific database compound notation -> f"[{db_name}][{value}]" inside category block.
    2. Lower Preference:   Direct shared fallback notation -> {value} inside category block.
    3. Global Fallback:     Matches across unnested structures via lookup_table.
    """
    val_str = str(value)
    
    # 1. Category-Specific Target Lookup (Applies dynamically to any matching key)
    if key in g_env_map and isinstance(g_env_map[key], dict):
        category_map = g_env_map[key]
        
        # PRIORITY 1: Highest Preference -> Database-specific override [sales_db][ftp_server_01]
        bracket_key = f"[{db_name}][{val_str}]"
        if bracket_key in category_map:
            if target_env in category_map[bracket_key]:
                return category_map[bracket_key][target_env]
                
        # PRIORITY 2: Lower Preference -> Direct fallback notation ftp_server_01
        if val_str in category_map:
            if target_env in category_map[val_str]:
                return category_map[val_str][target_env]

    # PRIORITY 3: Global Unnested Matrix Fallback
    if val_str in lookup_table:
        matched_block = lookup_table[val_str]
        if target_env in matched_block:
            return matched_block[target_env]
            
    # Suffix Splicing Handler
    elif val_str.endswith('_nt1'):
        cleaned_val = val_str[:-4]
        if cleaned_val in lookup_table:
            matched_block = lookup_table[cleaned_val]
            if target_env in matched_block:
                return matched_block[target_env]
                
    return value


def update_metadata_values(config_node, target_env, db_name, g_env_map, lookup_table):
    """
    NON-RECURSIVE: Loops key-by-key strictly through the root level of the metadata structure.
    """
    if not isinstance(config_node, dict):
        return

    for key in list(config_node.keys()):
        value = config_node[key]
        
        # CRITICAL: Skip entities section entirely during this run
        if key == "entities":
            logging.info("--> Skipping 'entities' section during global metadata update.")
            continue
        
        # Check for SPECIAL KEYS that have unique condition rules
        if key == "destination_database":
            updated_val = handle_special_destination_database(config_node, g_env_map, target_env)
            config_node[key] = updated_val
            logging.info(f"[Special Key Processed] '{key}' -> '{updated_val}'")
            continue

        # STANDARD KEY PROCESSING (Evaluates root values layer flatly, one key at a time)
        if isinstance(value, str):
            new_value = handle_standard_lookup(key, value, target_env, db_name, g_env_map, lookup_table)
            if new_value != value:
                config_node[key] = new_value
                logging.info(f"[Standard Key Processed] '{key}' | Old: '{value}' -> New: '{new_value}'")


def update_entities_only(entities_node, target_env, db_name, g_env_map, lookup_table):
    """
    SEPARATE FUNCTION (NON-RECURSIVE): Processes and updates values inside the entities block flatly.
    Handles lists of entity objects or direct entity dictionaries without cascading deep recursion.
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


def get_environment_map(db_name: str, src_env: str, src_container: str, env_name: str, src_metameta: dict):
    """
    Orchestrates configuration metadata translation by loading the global environment map
    and dynamically processing the keys.
    """
    global_map_file = os.path.join(SOURCE_ROOT, "global_environment_map.json")
    
    if not os.path.exists(global_map_file):
        logging.error(f"Global environment map missing during transformation at: {global_map_file}")
        return src_metameta

    with open(global_map_file, 'r') as f:
        g_env_map = json.load(f)

    # Automatically derive environment context metadata keys
    env_keys_set = auto_discover_env_keys(g_env_map)
    
    lookup_table = {}
    extract_mappings(g_env_map, env_keys_set, lookup_table)

    # Create a deep copy to safely update configuration values in memory
    working_meta = json.loads(json.dumps(src_metameta))

    # Run structural root key-by-key map translations flatly (Skipping entities inside this execution path)
    update_metadata_values(working_meta, env_name, db_name, g_env_map, lookup_table)

    return working_meta


# -----------------------------------------------------------------
# MOCK INFRASTRUCTURE (Replaces Azure Blob Storage SDK Hooks)
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


# -----------------------------------------------------------------
# CORE MIGRATION PROCESS
# -----------------------------------------------------------------
def run_migrate_metameta(db_name: str, src_env: str, tgt_env: str, src_container: str, tgt_container: str, env_name: str):
    src_metameta = get_src_metameta(db_name, src_env, src_container)
    if not src_metameta:
        return

    tgt_metameta = get_tgt_metameta(db_name, tgt_env, tgt_container)
    
    # Process metadata values utilizing our automated dynamic engine layout
    mapped_meta = get_environment_map(db_name, src_env, src_container, env_name, src_metameta)
    
    write_metameta_to_destination(db_name, tgt_env, mapped_meta, tgt_container)


# -----------------------------------------------------------------
# FULLY DYNAMIC LOCAL TESTING SUITE ENTRANCE
# -----------------------------------------------------------------
if __name__ == "__main__":
    print(">>> Beginning dynamic local emulation framework run...")
    
    local_execution_parameters = {
        "src_container": "local-src-container",
        "tgt_container": "local-tgt-container",
        "env_name": "prd",
        "split_plandata_production": "False"
    }
    
    global_map_file = os.path.join(SOURCE_ROOT, "global_environment_map.json")
    
    # 1. Verify Global Environment Master configuration exists before initializing loops
    if not os.path.exists(global_map_file):
        print(f"\n[!] Setup Needed: Global Environment Map file is missing.")
        print(f" -> Please drop your master configuration into: {global_map_file}\n")
    else:
        # 2. Dynamically scan for all child database profiles inside the SOURCE_ROOT folder
        if os.path.exists(SOURCE_ROOT):
            source_items = os.listdir(SOURCE_ROOT)
            db_folders = [item for item in source_items if os.path.isdir(os.path.join(SOURCE_ROOT, item))]
        else:
            db_folders = []

        if not db_folders:
            print(f"\n[!] Setup Needed: No database metadata folders found inside: {SOURCE_ROOT}")
            print(" -> Create a folder (e.g., 'my_database') and drop its metameta configuration inside.\n")
        else:
            print(f"--- Detected {len(db_folders)} database profile(s) to process: {db_folders} ---")
            
            # 3. Run the environment migration compiler over every discovered source database folder
            for db_name_target in db_folders:
                print(f"\n[Loop Execution] Starting mapping sequence for schema: '{db_name_target}'")
                
                target_db_dir = os.path.join(TARGET_ROOT, db_name_target)
                os.makedirs(target_db_dir, exist_ok=True)
                
                metameta_file = os.path.join(SOURCE_ROOT, db_name_target, f"{db_name_target}_metameta.json")
                
                if not os.path.exists(metameta_file):
                    print(f" -> [Skip] Target schema missing from database directory context: {metameta_file}")
                    continue
                
                run_migrate_metameta(
                    db_name_target,
                    "local_src", "local_tgt",
                    local_execution_parameters["src_container"],
                    local_execution_parameters["tgt_container"],
                    local_execution_parameters["env_name"]
                )
                print(f" -> [Success] Migration file written to: {target_db_dir}/{db_name_target}_metameta.json")
                
            print("\n>>> All discovered folder transformation loops safely completed.")
