import os
import json
import logging
import collections
from datetime import datetime

# Configure local console logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global Orchestration Configurations ---
reset_tgt_hwm = '1900/01/01'
reset_tgt_hwm_id = '0'
config_length = 10
split_length = 3
split_plandata_production = 'False'

# --- Local Directory Root Setup ---
LOCAL_STORAGE_ROOT = os.path.join(os.getcwd(), "mock_storage")
SOURCE_ROOT = os.path.join(LOCAL_STORAGE_ROOT, "source", "metadata")
TARGET_ROOT = os.path.join(LOCAL_STORAGE_ROOT, "target", "metadata")


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
    except json.JSONDecodeError as je:
        logging.error(f"CRITICAL SYNTAX ERROR: '{path}' contains broken JSON layout structure at line {je.lineno}. Error: {je.msg}")
        return None

def get_tgt_metameta(db_name: str, *args):
    path = os.path.join(TARGET_ROOT, db_name, f"{db_name}_metameta.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"Local target metameta file not found at: {path}. Assuming fresh run.")
        return None

def get_db_environment_map(db_name: str, *args):
    path = os.path.join(SOURCE_ROOT, db_name, f"{db_name}_environment_map.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def get_global_environment_map(*args):
    path = os.path.join(SOURCE_ROOT, "global_environment_map.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"CRITICAL: Local global_environment_map.json not found at: {path}")
        return None

def write_metameta_to_destination(db_name: str, account_url: str, metameta_dict: dict, container: str):
    target_dir = os.path.join(TARGET_ROOT, db_name)
    os.makedirs(target_dir, exist_ok=True)
    
    path = os.path.join(target_dir, f"{db_name}_metameta.json")
    with open(path, 'w') as f:
        json.dump(metameta_dict, f, indent=2)
    logging.info(f"Local file cleanly written to: {path}")


# Mock DB High Water Mark Utilities
class LocalMockSnowflakeUtils:
    def get_hwm_val_from_sql(self, server, db):
        logging.info(f"[Mock SQL] Fetching HWM values for Server: {server}, DB: {db}")
        return {"customer": "1900/01/01", "geohealth": "1900/01/01"}
        
    def update_hwm_val_to_sql(self, server, db, entity, value):
        logging.info(f"[Mock SQL] Saved high-water mark to DB: {entity} -> {value}")

ut = LocalMockSnowflakeUtils()

def replace_db_in_procedurename_per_env(procedure_name: str, env_map_database: dict, env: str):
    parts = procedure_name.strip().split('.')
    if len(parts) == 3:
        db_val = parts[0]
        if db_val.lower() in env_map_database:
            mapped_db = env_map_database[db_val.lower()][env]
            return f"{mapped_db}.{parts[1]}.{parts[2]}".upper()
    return procedure_name.upper()

def find_entity_meta_meta(meta, entity_name):
    for entity in meta.get('entities', []):
        if entity['source_entity'].lower() == entity_name.lower():
            return entity
    return None

def is_UK_HWM_match(tgt_entity, src_entity):
    return tgt_entity.get("merge_or_copy") == src_entity.get("merge_or_copy")


# -----------------------------------------------------------------
# COUPLING-FREE ENVIRONMENT MAPPING RULES
# -----------------------------------------------------------------
def handle_destination_database(val, root_metadata, g_env_map, env_name_clean, context=None):
    if root_metadata.get('source_type', '').lower() != 'snowflake':
        if val.lower() in g_env_map.get("Database", {}):
            return g_env_map["Database"][val.lower()][env_name_clean].upper()
    return val

def handle_destination_warehouse(val, root_metadata, g_env_map, env_name_clean, context=None):
    if root_metadata.get('destination_type', '').lower() == "sql server":
        if val.lower() in g_env_map.get("Server", {}):
            return g_env_map["Server"][val.lower()][env_name_clean]  # Kept as configured
    else:
        if val.lower() in g_env_map.get("Warehouse", {}):
            return g_env_map["Warehouse"][val.lower()][env_name_clean].upper()
    return val

def handle_source_database(val, root_metadata, g_env_map, env_name_clean, context=None):
    if root_metadata.get('source_type', '').lower() == "snowflake":
        if val.lower() in g_env_map.get("Database", {}):
            return g_env_map["Database"][val.lower()][env_name_clean].upper()
    else:
        if "SQLDatabase" in g_env_map and val.lower() in g_env_map["SQLDatabase"]:
            return g_env_map["SQLDatabase"][val.lower()][env_name_clean]  # Kept as configured
    return val

def handle_source_warehouse(val, root_metadata, g_env_map, env_name_clean, context=None):
    if root_metadata.get('source_type', '').lower() == "snowflake":
        if val.lower() in g_env_map.get("Warehouse", {}):
            return g_env_map["Warehouse"][val.lower()][env_name_clean].upper()
    return val

def handle_pattern_fields(val, root_metadata, g_env_map, env_name_clean, db_name_lower, context=None):
    if not isinstance(val, str):
        return val
    val_lower = val.lower()
    
    entity_name = ''
    if isinstance(context, dict):
        entity_name = context.get('source_entity', '').lower()
    
    lookups_to_try = []
    if db_name_lower:
        lookups_to_try.append(f'[{db_name_lower}]{val_lower}')
        lookups_to_try.append(f'[{db_name_lower}][{val_lower}]')
        
    if db_name_lower and entity_name:
        lookups_to_try.append(f'[{db_name_lower}][{entity_name}][{val_lower}]')
    if entity_name:
        lookups_to_try.append(f'[{entity_name}][{val_lower}]')
    lookups_to_try.extend([val_lower, val])

    for category, mappings in g_env_map.items():
        if not isinstance(mappings, dict):
            continue
        lowercase_mappings = {str(k).lower(): v for k, v in mappings.items()}
        for lookup in lookups_to_try:
            if lookup in lowercase_mappings:
                return lowercase_mappings[lookup][env_name_clean]
    return val


# -----------------------------------------------------------------
# DECOUPLED RECURSION TRANSLATION ENGINE
# -----------------------------------------------------------------
def replace_recursively(current_node, root_metadata, g_env_map, env_name_clean, db_name_lower, current_key=None, parent_dict=None):
    if root_metadata is None:
        root_metadata = current_node

    conditional_rules = {
        'destination_database': lambda v, context: handle_destination_database(v, root_metadata, g_env_map, env_name_clean, context),
        'destination_warehouse': lambda v, context: handle_destination_warehouse(v, root_metadata, g_env_map, env_name_clean, context),
        'source_database': lambda v, context: handle_source_database(v, root_metadata, g_env_map, env_name_clean, context),
        'source_warehouse': lambda v, context: handle_source_warehouse(v, root_metadata, g_env_map, env_name_clean, context),
        'ftp_host_name': lambda v, context: handle_pattern_fields(v, root_metadata, g_env_map, env_name_clean, db_name_lower, context),
        'default_ftp_host_name': lambda v, context: handle_pattern_fields(v, root_metadata, g_env_map, env_name_clean, db_name_lower, context),
        'to_uat': lambda v, context: handle_pattern_fields(v, root_metadata, g_env_map, env_name_clean, db_name_lower, context),
        'default_ftp_root_folder': lambda v, context: handle_pattern_fields(v, root_metadata, g_env_map, env_name_clean, db_name_lower, context),
        'root_folder': lambda v, context: handle_pattern_fields(v, root_metadata, g_env_map, env_name_clean, db_name_lower, context),
        'workspace_id': lambda v, context: handle_pattern_fields(v, root_metadata, g_env_map, env_name_clean, db_name_lower, context),
        'resource_id': lambda v, context: handle_pattern_fields(v, root_metadata, g_env_map, env_name_clean, db_name_lower, context)
    }

    if isinstance(current_node, dict):
        return {k: replace_recursively(v, root_metadata, g_env_map, env_name_clean, db_name_lower, current_key=k, parent_dict=current_node) for k, v in current_node.items()}
    elif isinstance(current_node, list):
        return [replace_recursively(item, root_metadata, g_env_map, env_name_clean, db_name_lower, current_key=current_key, parent_dict=parent_dict) for item in current_node]
    elif isinstance(current_node, str):
        # 1. Strict Intercept: Force upper casing only for specific required elements
        if current_key == 'external_stage_name':
            return f"{env_name_clean.strip().upper()}_CSV_STAGE"
            
        rule = conditional_rules.get(current_key)
        if rule:
            res_val = rule(current_node, context=parent_dict)
            # Enforce case guard strictly only for database, warehouse, stage, and procedure elements
            if current_key and any(x in current_key.lower() for x in ['database', 'warehouse', 'stage', 'procedure']):
                if isinstance(res_val, str):
                    res_val = res_val.upper()
            return res_val
            
        if current_key == 'post_execution_procedure':
            return replace_db_in_procedurename_per_env(current_node, g_env_map.get("Database", {}), env_name_clean)
        
        node_lower = current_node.lower()
        entity_name = parent_dict.get('source_entity', '').lower() if isinstance(parent_dict, dict) else ''
        
        lookups_to_try = []
        if db_name_lower:
            lookups_to_try.append(f'[{db_name_lower}]{node_lower}')
            lookups_to_try.append(f'[{db_name_lower}][{node_lower}]')
            
        if db_name_lower and entity_name:
            lookups_to_try.append(f'[{db_name_lower}][{entity_name}][{node_lower}]')
        if entity_name:
            lookups_to_try.append(f'[{entity_name}][{node_lower}]')
        lookups_to_try.extend([node_lower, current_node])
        
        for category, mappings in g_env_map.items():
            if not isinstance(mappings, dict):
                continue
            
            lowercase_mappings = {str(k).lower(): v for k, v in mappings.items()}
            for lookup in lookups_to_try:
                if lookup in lowercase_mappings:
                    resolved_val = lowercase_mappings[lookup][env_name_clean]
                    # Enforce uppercase transformations exclusively on infrastructure names
                    if current_key and any(x in current_key.lower() for x in ['database', 'warehouse', 'stage', 'procedure']):
                        if isinstance(resolved_val, str):
                            resolved_val = resolved_val.upper()
                    return resolved_val
                    
        return current_node
    return current_node


def get_environment_map(db_name: str, account_url: str, container: str, env_name: str, src_metameta: dict):
    env_name_clean = env_name.strip()
    db_name_lower = db_name.lower() if db_name else ""

    env_map = get_db_environment_map(db_name, account_url, container)
    if env_map:
        ret_env_map = {}
        for key in env_map.keys():
            if env_name_clean in env_map[key]:
                ret_env_map[key] = env_map[key][env_name_clean]
        return ret_env_map

    g_env_map = get_global_environment_map(db_name, account_url, container)
    if not g_env_map:
        return {}

    return replace_recursively(src_metameta, None, g_env_map, env_name_clean, db_name_lower)


# -----------------------------------------------------------------
# CORE MIGRATION PROCESS
# -----------------------------------------------------------------
def run_migrate_metameta(db_name: str, src_env: str, tgt_env: str, src_container: str, tgt_container: str, env_name: str):
    src_metameta = get_src_metameta(db_name, src_env, src_container)
    if not src_metameta:
        return

    tgt_metameta = get_tgt_metameta(db_name, tgt_env, tgt_container)
    mapped_meta = get_environment_map(db_name, src_env, src_container, env_name, src_metameta)
    
    if mapped_meta and isinstance(mapped_meta, dict):
        src_metameta = mapped_meta

    final_src_metameta_entities = list()

    if len(src_metameta.get('entities', [])) > 0:
        resolved_server = src_metameta.get('source_server', '')
        resolved_db = src_metameta.get('source_database', '')
        
        db_hwm_values = ut.get_hwm_val_from_sql(resolved_server, resolved_db) if resolved_server and resolved_db else {}

        for src_entity in src_metameta['entities']:
            s_entity = src_entity["source_entity"]
            s_entity_lw = s_entity.lower()

            logging.info(f"Processing entity {s_entity}")

            mapped_entity = get_environment_map(db_name, src_env, src_container, env_name, src_entity)
            if isinstance(mapped_entity, dict):
                src_entity.update(mapped_entity)

            if ("delete_path" not in src_entity) or ("delete_path" in src_entity and src_entity["delete_path"] == "false"):
                src_entity.pop("delete_schedule", None)
                src_entity.pop("soft_delete", None)
                src_entity.pop("delete_path", None)

            if "hwm_col" not in src_entity and "hwm_id" not in src_entity:
                final_src_metameta_entities.append(src_entity)
                continue

            hwm_value = reset_tgt_hwm if "hwm_col" in src_entity.keys() else reset_tgt_hwm_id
            reset_hwm_value = hwm_value

            if s_entity_lw in db_hwm_values:
                hwm_value = db_hwm_values[s_entity_lw]
            
            if tgt_metameta:
                old_entity = find_entity_meta_meta(tgt_metameta, s_entity)
                if old_entity and old_entity.get("merge_or_copy") != src_entity.get("merge_or_copy"):
                    hwm_value = reset_hwm_value

            db_hwm_values[s_entity_lw] = hwm_value
            src_entity.pop("hwm_val", None)
            final_src_metameta_entities.append(src_entity)

        if resolved_server and resolved_db:
            for entity_key, val in db_hwm_values.items():
                ut.update_hwm_val_to_sql(resolved_server, resolved_db, entity_key, val)

    if final_src_metameta_entities:
        src_metameta['entities'] = final_src_metameta_entities
        
    write_metameta_to_destination(db_name, tgt_env, src_metameta, tgt_container)


# -----------------------------------------------------------------
# DYNAMIC TEST SUITE INITIALIZER
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
    
    if not os.path.exists(global_map_file):
        print(f"\n[!] Setup Needed: Global Environment Map file is missing: {global_map_file}\n")
    else:
        if os.path.exists(SOURCE_ROOT):
            source_items = os.listdir(SOURCE_ROOT)
            db_folders = [item for item in source_items if os.path.isdir(os.path.join(SOURCE_ROOT, item))]
        else:
            db_folders = []

        if not db_folders:
            print(f"\n[!] Setup Needed: No database metadata folders found inside: {SOURCE_ROOT}\n")
        else:
            print(f"--- Detected {len(db_folders)} database profile(s) to process: {db_folders} ---")
            
            for db_name_target in db_folders:
                print(f"\n[Loop Execution] Starting mapping sequence for schema: '{db_name_target}'")
                
                target_db_dir = os.path.join(TARGET_ROOT, db_name_target)
                os.makedirs(target_db_dir, exist_ok=True)
                
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
                print(f" -> [Success] Migration file written to: {target_db_dir}/{db_name_target}_metameta.json")
                
            print("\n>>> All discovered folder transformation loops safely completed.")
