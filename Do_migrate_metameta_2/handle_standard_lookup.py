def handle_standard_lookup(key, value, target_env, db_name, g_env_map, entity_name=None):
    val_str = str(value)

    if key in g_env_map and isinstance(g_env_map[key], dict):
        category_map = g_env_map[key]

        # Case-insensitive map for lookups
        ci_category_map = {
            k.lower(): (k, v)
            for k, v in category_map.items()
        }

        # TIER 1
        if entity_name:
            lookup_key = f"[{db_name}][{entity_name}][{val_str}]".lower()

            if lookup_key in ci_category_map:
                original_key, env_map = ci_category_map[lookup_key]

                if target_env in env_map:
                    return env_map[target_env]

        # TIER 2
        lookup_key = f"[{db_name}][{val_str}]".lower()

        if lookup_key in ci_category_map:
            original_key, env_map = ci_category_map[lookup_key]

            if target_env in env_map:
                return env_map[target_env]

        # TIER 3
        lookup_key = val_str.lower()

        if lookup_key in ci_category_map:
            original_key, env_map = ci_category_map[lookup_key]

            if target_env in env_map:
                return env_map[target_env]

    return value
