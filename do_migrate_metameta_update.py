RESET_HWM_DATE = "1900/01/01"
RESET_HWM_ID = "0"


def is_hwm_match(src_entity, tgt_entity):
    if (
        "hwm_col" in src_entity
        and "hwm_col" in tgt_entity
    ):
        return (
            src_entity["hwm_col"]
            == tgt_entity["hwm_col"]
        )

    if (
        "hwm_id" in src_entity
        and "hwm_id" in tgt_entity
    ):
        return (
            src_entity["hwm_id"]
            == tgt_entity["hwm_id"]
        )

    return False


def find_entity(metameta, entity_name):
    if not metameta:
        return None

    for entity in metameta.get("entities", []):
        if (
            entity.get("source_entity", "").lower()
            == entity_name.lower()
        ):
            return entity

    return None

def run_migrate_metameta(
    db_name: str,
    env_name: str
):
    global_map = get_global_environment_map("source")

    lookup = create_replacement_lookup(
        global_map,
        env_name
    )

    src_metameta = get_src_metameta(
        db_name,
        None,
        None
    )

    tgt_metameta = get_tgt_metameta(
        db_name,
        None,
        None
    )

    if not src_metameta:
        print(f"Source metadata not found for {db_name}")
        return

    # Replace all values recursively
    updated_metameta = replace_recursively(
        src_metameta,
        lookup
    )

    # Read current HWM values
    db_hwm_values = get_hwm_values_from_db(
        db_name
    )

    final_entities = []

    for entity in updated_metameta.get(
        "entities",
        []
    ):

        entity_name = entity.get(
            "source_entity",
            ""
        ).lower()

        old_entity = find_entity(
            tgt_metameta,
            entity_name
        )

        if (
            "hwm_col" in entity
            or "hwm_id" in entity
        ):

            if "hwm_col" in entity:
                hwm_value = RESET_HWM_DATE
            else:
                hwm_value = RESET_HWM_ID

            # Keep DB HWM if available
            if entity_name in db_hwm_values:
                hwm_value = db_hwm_values[
                    entity_name
                ]

            # Compare with target metadata
            if old_entity:

                merge_match = (
                    old_entity.get(
                        "merge_or_copy"
                    )
                    ==
                    entity.get(
                        "merge_or_copy"
                    )
                )

                hwm_match = is_hwm_match(
                    entity,
                    old_entity
                )

                if not (
                    merge_match
                    and hwm_match
                ):
                    if "hwm_col" in entity:
                        hwm_value = RESET_HWM_DATE
                    else:
                        hwm_value = RESET_HWM_ID

            db_hwm_values[
                entity_name
            ] = hwm_value

            entity["hwm_val"] = hwm_value

        final_entities.append(entity)

    updated_metameta["entities"] = final_entities

    write_hwm_values_to_db(
        db_name,
        db_hwm_values
    )

    write_metameta_to_destination(
        db_name,
        None,
        updated_metameta,
        None
    )

    print(
        f"Completed migration for {db_name}"
    )
