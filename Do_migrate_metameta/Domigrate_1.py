import logging

def get_environment_map(
    db_name: str,
    account_url: str,
    container: str,
    env_name: str,
    src_metameta: dict
):
    # 1. Try DB-specific map first
    env_map = get_db_environment_map(db_name, account_url, container)
    if env_map:
        ret_env_map = {}
        for key in env_map.keys():
            if env_name in env_map[key]:
                ret_env_map[key] = env_map[key][env_name]
        return ret_env_map

    # 2. Fetch Global Map
    g_env_map = get_global_environment_map(db_name, account_url, container)
    
    # -------------------------------------------------------------
    # RULE REGISTRY: Custom logic handlers
    # -------------------------------------------------------------
    def handle_destination_database(val, context=None):
        if src_metameta.get('source_type', '').lower() != 'snowflake':
            if val.lower() in g_env_map.get("Database", {}):
                return g_env_map["Database"][val.lower()][env_name].upper()
        return val

    def handle_destination_warehouse(val, context=None):
        if src_metameta.get('destination_type', '').lower() == "sql server":
            if val.lower() in g_env_map.get("Server", {}):
                return g_env_map["Server"][val.lower()][env_name]
        else:
            if val.lower() in g_env_map.get("Warehouse", {}):
                return g_env_map["Warehouse"][val.lower()][env_name].upper()
        return val

    def handle_source_database(val, context=None):
        if src_metameta.get('source_type', '').lower() == "snowflake":
            if val.lower() in g_env_map.get("Database", {}):
                return g_env_map["Database"][val.lower()][env_name].upper()
        else:
            if "SQLDatabase" in g_env_map and val.lower() in g_env_map["SQLDatabase"]:
                return g_env_map["SQLDatabase"][val.lower()][env_name]
        return val

    def handle_source_warehouse(val, context=None):
        if src_metameta.get('source_type', '').lower() == "snowflake":
            if val.lower() in g_env_map.get("Warehouse", {}):
                return g_env_map["Warehouse"][val.lower()][env_name].upper()
        return val

    def handle_pattern_fields(val, context=None):
        if not isinstance(val, str):
            return val
            
        val_lower = val.lower()
        entity_name = context.get('source_entity', '').lower() if isinstance(context, dict) else ''
        
        # Build the exact tiered lookup sequences requested
        lookups_to_try = []
        if db_name and entity_name:
            lookups_to_try.append(f'[{db_name.lower()}][{entity_name}][{val_lower}]') # [db][entity][value]
        if db_name:
            lookups_to_try.append(f'[{db_name.lower()}][{val_lower}]')               # [db][value]
        if entity_name:
            lookups_to_try.append(f'[{entity_name}][{val_lower}]')                   # [entity][value]
            
        lookups_to_try.extend([val_lower, val])                                      # value / original value

        categories = ['ftp_host_name', 'default_ftp_host_name', 'to_uat', 'default_ftp_root_folder']
        
        for category in categories:
            category_dict = g_env_map.get(category, {})
            for lookup in lookups_to_try:
                if lookup in category_dict:
                    return category_dict[lookup][env_name]
        return val

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
    # RECURSIVE REPLACEMENT ENGINE
    # -------------------------------------------------------------
    def replace_recursively(node, current_key=None, parent_dict=None):
        # Case A: Dictionary (Track parent_dict for context)
        if isinstance(node, dict):
            return {k: replace_recursively(v, current_key=k, parent_dict=node) for k, v in node.items()}
        
        # Case B: List / Array (Pass down the parent_dict context)
        elif isinstance(node, list):
            return [replace_recursively(item, current_key=current_key, parent_dict=parent_dict) for item in node]
        
        # Case C: String values
        elif isinstance(node, str):
            if current_key in conditional_rules:
                return conditional_rules[current_key](node, context=parent_dict)
            
            if current_key == 'post_execution_procedure':
                return replace_db_in_procedurename_per_env(
                    node, g_env_map.get("Database", {}), env_name
                )
            
            # Fallback global lookup engine
            node_lower = node.lower()
            for category, mappings in g_env_map.items():
                if not isinstance(mappings, dict):
                    continue
                    
                if node_lower in mappings:
                    resolved_val = mappings[node_lower][env_name]
                    if current_key and any(x in current_key.lower() for x in ['database', 'warehouse']):
                        resolved_val = resolved_val.upper()
                    return resolved_val
                elif node in mappings:
                    return mappings[node][env_name]
            
            return node
            
        return node

    return replace_recursively(src_metameta)
