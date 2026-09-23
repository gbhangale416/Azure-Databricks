# EDI specific changes for DMAP837
if "ftp_host_name" in src_entity:

    env_map_keyvalue = get_environment_map_for_key(
        db_name,
        src_env,
        src_container,
        "ftp_host_name"
    )

    ftp_host_name_val = src_entity["ftp_host_name"].lower()

    # source_entity OR file_type
    source_entity_val = (
        src_entity.get("source_entity")
        or src_entity.get("file_type")
    ).lower()

    # [db_name][source_entity]ftp_host_name
    ftp_host_name_key = (
        f"[{db_name.lower()}]"
        f"[{source_entity_val}]"
        f"{ftp_host_name_val}"
    )

    logging.info(
        f"FTP host mapping key: {ftp_host_name_key}"
    )

    if ftp_host_name_key in env_map_keyvalue:
        rt_ftp_host_name = env_map_keyvalue[ftp_host_name_key][env_name]
    else:
        logging.warning(
            f"FTP host mapping not found: {ftp_host_name_key}"
        )
        rt_ftp_host_name = ftp_host_name_val

    src_entity["ftp_host_name"] = rt_ftp_host_name


if "ftp_user_name" in src_entity:

    env_map_keyvalue = get_environment_map_for_key(
        db_name,
        src_env,
        src_container,
        "ftp_user_name"
    )

    ftp_user_name_val = src_entity["ftp_user_name"].lower()

    # [db_name][source_entity]ftp_user_name
    ftp_user_name_key = (
        f"[{db_name.lower()}]"
        f"[{source_entity_val}]"
        f"{ftp_user_name_val}"
    )

    logging.info(
        f"FTP user mapping key: {ftp_user_name_key}"
    )

    if ftp_user_name_key in env_map_keyvalue:
        rt_ftp_user_name = env_map_keyvalue[ftp_user_name_key][env_name]
    else:
        logging.warning(
            f"FTP user mapping not found: {ftp_user_name_key}"
        )
        rt_ftp_user_name = ftp_user_name_val

    src_entity["ftp_user_name"] = rt_ftp_user_name
