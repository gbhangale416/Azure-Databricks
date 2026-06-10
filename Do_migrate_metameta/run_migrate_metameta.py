import logging

# Ensure logging is configured
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_environment_map(
    db_name: str,
    account_url: str,
    container: str,
    env_name: str,
    src_metameta: dict
) -> dict:
    """
    Recursively maps and updates a metameta dictionary configuration based on 
    database-specific or global environment map lookup rules.
    """
    # Normalize environment and database names safely
    env_name_clean = env_name.strip()
    db_name_lower = db_name.lower() if db_name else ""

    # 1. Try DB-Specific Environment Map First (Bypasses global map if found)
    env_map = get_db_environment_map(db_name, account_url, container)
    if env_map:
        logging.info(f"Using database-specific environment map for {db_name}")
        ret_env_map = {}
        for key in ['source_server', 'destination_database', 'destination_warehouse']:
            if key in env_map and env_name_clean in env_map[key]:
                ret_env_map[key] = env_map[key][env_name_clean]
        
        # Apply these flat updates directly to a copy of the source metadata
        final_meta = src_metameta.copy()
        for k, v in ret_env_map.items():
            final_meta[k] = v
        return final_meta

    # 2. Fallback to Global Environment Map Processing
    logging.info(f"Falling back to Global Environment Map processing for {db_name}")
    g_env_map = get_global_environment_map(db_name, account_url, container)
    if not g_env_map:
        logging.warning("Global environment map could not be retrieved. Returning source metadata as-is.")
        return src_metameta

    # -------------------------------------------------------------
    # RULE REGISTRY: Custom Conditional Logic Closures
    # -------------------------------------------------------------
    def handle_destination_database(val, context=None):
        if src_metameta.get('source_type', '').lower() != 'snowflake':
            if val.lower() in g_env_map.get("Database", {}):
                return g_env_map["Database"][val.lower()][env_name_clean].upper()
        return val

    def handle_destination_warehouse(val, context=None):
        if src_metameta.get('destination_type', '').lower() == "sql server":
            if val.lower() in g_env_map.get("Server", {}):
                return g_env_map["Server"][val.lower()][env_name_clean]
        else:
            if val.lower() in g_env_map.get("Warehouse", {}):
                return g_env_map["Warehouse"][val.lower()][env_name_clean].upper()
        return val

    def handle_source_database(val, context=None):
        if src_metameta.get('source_type', '').lower() == "snowflake":
            if val.lower() in g_env_map.get("Database", {}):
                return g_env_map["Database"][val.lower()][env_name_clean].upper()
        else:
            if "SQLDatabase" in g_env_map and val.lower() in g_env_map["SQLDatabase"]:
                return g_env_map["SQLDatabase"][val.lower()][env_name_clean]
        return val

    def handle_source_warehouse(val, context=None):
        if src_metameta.get('source_type', '').lower() == "snowflake":
            if val.lower() in g_env_map.get("Warehouse", {}):
                return g_env_map["Warehouse"][val.lower()][env_name_clean].upper()
        return val

    def handle_pattern_fields(val, context=None):
        if not isinstance(val, str):
            return val
            
        val_lower = val.lower()
        entity_name = context.get('source_entity', '').lower() if isinstance(context, dict) else ''
        
        # Core Requirement: Context-aware Hierarchical priority sequence list
        lookups_to_try = []
        if db_name_lower and entity_name:
            lookups_to_try.append(f'[{db_name_lower}][{entity_name}][{val_lower}]') # [db][entity][value]
        if db_name_lower:
            lookups_to_try.append(f'[{db_name_lower}][{val_lower}]')               # [db][value]
        if entity_name:
            lookups_to_try.append(f'[{entity_name}][{val_lower}]')                   # [entity][value]
            
        lookups_to_try.extend([val_lower, val])                                      # value / original raw value

        # Categories that utilize pattern context checks
        pattern_categories = ['ftp_host_name', 'default_ftp_host_name', 'to_uat', 'default_ftp_root_folder']
        
        for category in pattern_categories:
            category_dict = g_env_map.get(category, {})
            for lookup in lookups_to_try:
                if lookup in category_dict:
                    return category_dict[lookup][env_name_clean]
        return val

    # Map target metadata keys to their respective logic routines
    conditional_rules = {
        'destination_database': handle_destination_database,
        'destination_warehouse': handle_destination_warehouse,
        'source_database': handle_source_database,
        'source_warehouse': handle_source_warehouse,
        'ftp_host_name': handle_pattern_fields,
        'default_ftp_host_name': handle_pattern_fields,
        'to_uat': handle_pattern_fields,
        'default_ftp_root_folder': handle_pattern_fields
    }

    # -------------------------------------------------------------
    # RECURSIVE ENGINE CLOSURE
    # -------------------------------------------------------------
    def replace_recursively(node, current_key=None, parent_dict=None):
        # Case A: Handle Dictionary trees
        if isinstance(node, dict):
            return {k: replace_recursively(v, current_key=k, parent_dict=node) for k, v in node.items()}
        
        # Case B: Handle List / Object Array collections (e.g., 'entities')
        elif isinstance(node, list):
            return [replace_recursively(item, current_key=current_key, parent_dict=parent_dict) for item in node]
        
        # Case C: Parse String nodes
        elif isinstance(node, str):
            # Check explicit structural logic rules first
            if current_key in conditional_rules:
                return conditional_rules[current_key](node, context=parent_dict)
            
            # Check special database replacement regex rule
            if current_key == 'post_execution_procedure':
                return replace_db_in_procedurename_per_env(
                    node, g_env_map.get("Database", {}), env_name_clean
                )
            
            # Fallback Pattern: Completely dynamic scan for any unmapped/new keys
            node_lower = node.lower()
            for category, mappings in g_env_map.items():
                if not isinstance(mappings, dict):
                    continue
                    
                if node_lower in mappings:
                    resolved_val = mappings[node_lower][env_name_clean]
                    # Automatically enforce upper-case naming conventions for database components
                    if current_key and any(x in current_key.lower() for x in ['database', 'warehouse']):
                        resolved_val = resolved_val.upper()
                    return resolved_val
                elif node in mappings:
                    return mappings[node][env_name_clean]
            
            return node
            
        # Case D: Return integers, booleans, or null elements as-is
        return node

    # Process metadata config object from its root element node
    return replace_recursively(src_metameta)


def run_migrate_metameta(
    db_name: str,
    src_env: str,
    tgt_env: str,
    src_container: str,
    tgt_container: str,
    env_name: str
) -> None:
    """
    Main orchestration function to fetch metadata configs, migrate them safely 
    across targets, and commit the newly rendered file back to storage.
    """
    # 1. Fetch source configuration metadata file
    src_metameta = get_src_metameta(db_name, src_env, src_container)
    if not src_metameta:
        logging.info(f"Nothing to process. Metameta for {db_name} not found.")
        return

    # 2. Check for matching targeted metadata structures
    tgt_metameta = get_tgt_metameta(db_name, tgt_env, tgt_container)
    if not tgt_metameta:
        logging.info(f"There is no target metameta found for {db_name}.")

    # 3. Generate fully translated environment map configuration
    migrated_metameta = get_environment_map(
        db_name, src_env, src_container, env_name, src_metameta
    )

    # 4. Handle isolated transformation variables not managed by map registries
    if "external_stage_name" in migrated_metameta:
        migrated_metameta['external_stage_name'] = f"{env_name.strip().upper()}_CSV_STAGE"

    # 5. Output newly updated dynamic structure to target repository
    write_metameta_to_destination(
        db_name, tgt_env, migrated_metameta, tgt_container
    )
    logging.info(f"Successfully migrated and finalized metadata file for database: {db_name}")


# -------------------------------------------------------------
# PIPELINE DOWNSTREAM HOOKS / STUBS 
# (Replace these with your actual system infrastructure modules)
# -------------------------------------------------------------
def get_db_environment_map(db_name, account_url, container):
    # Returns specific DB environment details if applicable; else None
    return None

def get_global_environment_map(db_name, account_url, container):
    # Mock representation mimicking global_environment_map.json
    return {
        "Database": {
            "coedw_test": {"dev": "coedw_dev", "tst": "coedw_test", "prd": "coedw_prod"}
        },
        "Warehouse": {
            "wh_gen1_elt_c4_xs_dev_test": {
                "dev": "WH_GEN1_ELT_C4_XS_DEV", 
                "tst": "WH_GEN1_ELT_C4_XS_DEV_TEST", 
                "prd": "WH_GEN1_ELT_C4_XS_PROD"
            }
        },
        "ftp_host_name": {
            "[salesdb][customer][ftp_prod]": {"dev": "dev_ftp_cust", "prd": "prod_ftp_customer_hub"},
            "[salesdb][ftp_prod]": {"dev": "dev_ftp_fallback", "prd": "prod_ftp_fallback_hub"},
            "ftp_prod": {"dev": "dev_generic_ftp", "prd": "prod_generic_ftp"}
        }
    }

def get_src_metameta(db_name, src_env, src_container):
    return {}

def get_tgt_metameta(db_name, tgt_env, tgt_container):
    return {}

def write_metameta_to_destination(db_name, tgt_env, src_metameta, tgt_container):
    pass

def replace_db_in_procedurename_per_env(procedure_name, database_map, env_name):
    return procedure_name
