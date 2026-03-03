import re

def replace(query, db):

    if db not in env_stage_list:
        return query

    target_stage = env_stage_list[db]

    pattern = r"STAGE\.(DEV|TST|PRD|PREPROD)_CSV_STAGE"

    return re.sub(pattern, target_stage, query)


def replace(query, db):

    if db not in env_stage_list:
        return query

    target_stage = env_stage_list[db]

    # Match STAGE.DEV_CSV_STAGE / STAGE.TST_CSV_STAGE etc.
    pattern = r"\bSTAGE\.(DEV|TST|PRD|PREPROD)_CSV_STAGE\b"

    new_query = re.sub(pattern, target_stage, query)

    return new_query



import re

def get_stage_name_by_env(query, db):
    print("get_stage_name_by_env() - Starting stage replacement")
    print(f"get_stage_name_by_env() - Input DB: {db}")

    if not db:
        print("get_stage_name_by_env() - DB is empty or None. Returning original query.")
        return query

    if db not in env_stage_list:
        print(f"get_stage_name_by_env() - DB '{db}' not found in env_stage_list. Returning original query.")
        return query

    target_stage = env_stage_list[db]
    print(f"get_stage_name_by_env() - Target stage resolved to: {target_stage}")

    pattern = r"STAGE\.[A-Z_]+_CSV_STAGE"
    print(f"get_stage_name_by_env() - Using regex pattern: {pattern}")

    updated_query, count = re.subn(pattern, target_stage, query)

    print(f"get_stage_name_by_env() - Total replacements made: {count}")

    if count > 0:
        print("get_stage_name_by_env() - Stage replacement successful.")
    else:
        print("get_stage_name_by_env() - No matching stage found in query.")

    return updated_query
