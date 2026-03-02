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
