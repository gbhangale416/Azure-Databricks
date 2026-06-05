import logging
import os
import azure.functions as func
import json
import collections
from azure.storage.blob import BlobClient
from azure.storage.blob import ContainerClient
import snowflake_utils.utils as ut
import pytz
from datetime import datetime

reset_tgt_hwm = '1900/01/01'
reset_tgt_hwm_id = '0'

config_length = 10
split_length = 3
split_plandata_production = 'False'

def main(params: dict):
    db_names = params['db_names']
    src_container = params['src_container']
    tgt_container = params['tgt_container']
    env_name = params['env_name']
    adf_type = params.get("adf_type", "edw")
    global split_plandata_production
    split_plandata_production = params['split_plandata_production']

    if adf_type and adf_type.lower() == 'edi':
        tgt_env = os.environ['AzureBlobStorageEDIConnectionString']
    else:
        tgt_env = os.environ['AzureBlobStorageConnectionString']

    src_env = os.environ['AzureStageBlobStorageConnectionString']

    # tgt_env = read_parameters(req, 'tgt_env')
    # src_env = read_parameters(req, 'src_env')

    if db_names and len(db_names.strip()) > 0:
        db_list = [db.strip() for db in db_names.split(",")]
    else:
        db_list = get_db_list(src_env, src_container)

    logging.info(f'Running for databases = {db_list}. total : {len(db_list)}')

    for db_name in db_list:
        logging.info(f"Processing db {db_name}")
        logging.info(
            f"db_name:, {src_env}, {tgt_env}, {src_container}, "
            f"{tgt_container}, {env_name}"
        )

        run_migrate_metadata(
            db_name,
            src_env,
            tgt_env,
            src_container,
            tgt_container,
            env_name
        )

        logging.info(f'Completed db {db_name}')

    logging.info("Completed migration successfully")

    return "Success"


def get_db_list(account_url: str, container: str):
    container_client = ContainerClient.from_connection_string(account_url, container)
    blob_list = container_client.list_blobs()

    db_list = set()
    name_list = [blob.name for blob in blob_list]

    for blob_name in name_list:
        if blob_name.find('metadata/') != -1:
            blob_name = blob_name[len("metadata/"):]
            blob_name = blob_name[0:blob_name.find('/')]
            db_list.add(blob_name)

    return list(db_list)


def find_entity_meta_meta(meta, entity_name):
    for entity in meta['entities']:
        if entity['source_entity'].lower() == entity_name.lower():
            return entity

    return None

def is_UK_HWM_match(tgt_entity, src_entity):
    ismerge_tgt = tgt_entity["merge_or_copy"]
    ismerge_src = src_entity["merge_or_copy"]

    if ismerge_tgt == ismerge_src:
        if ismerge_tgt == "merge" and ismerge_src == "merge":
            if (
                len(tgt_entity["merge_check_cols"]) > 0 and
                len(src_entity["merge_check_cols"]) > 0
            ):
                if (
                    collections.Counter(tgt_entity["merge_check_cols"]) ==
                    collections.Counter(src_entity["merge_check_cols"]) and
                    is_hwm_match(tgt_entity, src_entity)
                ):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return True
    else:
        return False


def is_hwm_match(tgt_entity, src_entity):
    if "hwm_col" in tgt_entity and "hwm_col" in src_entity:
        if tgt_entity["hwm_col"] == src_entity["hwm_col"]:
            return True
        else:
            return False

    if "hwm_id" in tgt_entity and "hwm_id" in src_entity:
        if tgt_entity["hwm_id"] == src_entity["hwm_id"]:
            return True
        else:
            return False

    return False
	
def get_src_metameta(db_name: str, account_url: str, container: str):
    try:
        metameta_blob_client = BlobClient.from_connection_string(
            account_url,
            container_name=container,
            blob_name=f"metadata/{db_name}/{db_name}_metameta.json"
        )

        metameta_ssdl = metameta_blob_client.download_blob()
        metameta_blob_text = metameta_ssdl.content_as_text()
        metameta_dict = json.loads(metameta_blob_text)

    except Exception as e:
        logging.error(f"Source blob not found: {e}")
        return None

    return metameta_dict

def read_merge_tgt_metameta(db_name: str, account_url: str, container: str):
    config_length = config_length + 1
    metameta_dict = dict()

    for i in range(0, config_length):
        if i == 0:
            metameta_blob_client = BlobClient.from_connection_string(
                account_url,
                container_name=container,
                blob_name=f"{db_name}/{db_name}_metameta.json"
            )

            if metameta_blob_client.exists():
                metameta_ssdl = metameta_blob_client.download_blob()
                metameta_blob_text = metameta_ssdl.content_as_text()
                metameta_dict_set = json.loads(metameta_blob_text)

                if not metameta_dict_set is None:
                    metameta_dict.update(metameta_dict_set)

        else:
            db_name2 = f"{db_name}_Set_{i}"

            metameta_blob_client = BlobClient.from_connection_string(
                account_url,
                container_name=container,
                blob_name=f"{db_name2}/{db_name2}_metameta.json"
            )

            if metameta_blob_client.exists():
                metameta_ssdl = metameta_blob_client.download_blob()
                metameta_blob_text = metameta_ssdl.content_as_text()
                metameta_dict_set = json.loads(metameta_blob_text)

                if len(metameta_dict) == 0:
                    metameta_dict.update(metameta_dict_set)
                else:
                    metameta_dict['entities'].extend(
                        metameta_dict_set['entities']
                    )

    return metameta_dict

def get_tgt_metameta(db_name: str, account_url: str, container: str):
    try:
        if split_plandata_production == 'True' and db_name == 'plandata_Production':
            metameta_dict = read_merge_tgt_metameta(
                db_name,
                account_url,
                container
            )
        else:
            metameta_blob_client = BlobClient.from_connection_string(
                account_url,
                container_name=container,
                blob_name=f"{db_name}/{db_name}_metameta.json"
            )

            metameta_ssdl = metameta_blob_client.download_blob()
            metameta_blob_text = metameta_ssdl.content_as_text()
            metameta_dict = json.loads(metameta_blob_text)

    except Exception as e:
        logging.error(f"Target blob not found: {e}")
        return None

    return metameta_dict


def replace_db_in_procedurename_per_env(
    procedure_name: str,
    env_map_database: dict,
    env: str
):
    rt_procedure_name = procedure_name
    procedure_name_parts = procedure_name.strip().split('.')

    if len(procedure_name_parts) == 3:
        procedure_name_db_val = procedure_name_parts[0]
        rt_procedure_db = procedure_name_db_val

        if procedure_name_db_val.lower() in env_map_database.keys():
            rt_procedure_name_db = env_map_database[
                procedure_name_db_val.lower()
            ][env]

            rt_procedure_name = (
                f"{rt_procedure_name_db}."
                f"{procedure_name_parts[1]}."
                f"{procedure_name_parts[2]}"
            )

    return rt_procedure_name.upper()

def get_db_environment_map(db_name: str, account_url: str, container: str):
    try:
        env_blob_client = BlobClient.from_connection_string(
            account_url,
            container_name=container,
            blob_name=f"metadata/{db_name}/{db_name}_environment_map.json"
        )

        env_ssdl = env_blob_client.download_blob()
        env_blob_text = env_ssdl.content_as_text()
        environment_map = json.loads(env_blob_text)

    except Exception as e:
        logging.error(f"Environment map not found in source: {e}")
        return None

    return environment_map


def get_global_environment_map(db_name: str, account_url: str, container: str):
    try:
        env_blob_client = BlobClient.from_connection_string(
            account_url,
            container_name=container,
            blob_name="metadata/global_environment_map.json"
        )

        env_ssdl = env_blob_client.download_blob()
        env_blob_text = env_ssdl.content_as_text()
        environment_map = json.loads(env_blob_text)

    except Exception as e:
        logging.error(f"Global environment map not found in source: {e}")
        return None

    return environment_map
	
def get_environment_map_for_key(
    db_name: str,
    account_url: str,
    container: str,
    search_key: str
):
    try:
        ret_env_map_keyvalue = {}

        env_map = get_db_environment_map(
            db_name,
            account_url,
            container
        )

        if not env_map:
            env_map = get_global_environment_map(
                db_name,
                account_url,
                container
            )

        if search_key.strip() in env_map.keys():
            ret_env_map_keyvalue = env_map[search_key.strip()]

    except Exception as e:
        logging.error(
            f"get_environment_map_for_key(): Unexpected error: {e}"
        )
        return None

    return ret_env_map_keyvalue

def get_environment_map(
    db_name: str,
    account_url: str,
    container: str,
    env_name: str,
    src_metameta: dict
):
    ret_env_map = {}

    env_map = get_db_environment_map(
        db_name,
        account_url,
        container
    )

    if env_map:
        ret_env_map['source_server'] = \
            env_map['source_server'][env_name]

        ret_env_map['destination_database'] = \
            env_map['destination_database'][env_name]

        ret_env_map['destination_warehouse'] = \
            env_map['destination_warehouse'][env_name]

    else:
        g_env_map = get_global_environment_map(
            db_name,
            account_url,
            container
        )

        logging.info(g_env_map.keys())

        if 'source_server' in src_metameta:
            src_server_val = src_metameta['source_server']
            rt_server = src_server_val

            if src_server_val.lower() in g_env_map["Server"]:
                rt_server = g_env_map["Server"][
                    src_server_val.lower()
                ][env_name]

            ret_env_map['source_server'] = rt_server

        if 'destination_server' in src_metameta:
            dest_server_val = src_metameta['destination_server']
            rt_dest_server = dest_server_val

            if dest_server_val.lower() in g_env_map["Server"]:
                rt_dest_server = g_env_map["Server"][
                    dest_server_val.lower()
                ][env_name]

            ret_env_map['destination_server'] = rt_dest_server

        if 'destination_database' in src_metameta:
            dest_db_val = src_metameta['destination_database']
            rt_dest_db = dest_db_val

            if (
                'source_type' not in src_metameta or
                src_metameta['source_type'].lower() != 'snowflake'
            ):
                if dest_db_val.lower() in g_env_map["Database"]:
                    rt_dest_db = g_env_map["Database"][
                        dest_db_val.lower()
                    ][env_name]

                    rt_dest_db = rt_dest_db.upper()

            ret_env_map['destination_database'] = rt_dest_db
			
        if 'destination_warehouse' in src_metameta:
            dest_wh_val = src_metameta['destination_warehouse']
            rt_dest_wh = dest_wh_val

            if (
                'destination_type' in src_metameta and
                src_metameta['destination_type'].lower() == "sql server"
            ):
                if dest_wh_val.lower() in g_env_map["Server"]:
                    rt_dest_wh = g_env_map["Server"][
                        dest_wh_val.lower()
                    ][env_name]
            else:
                if dest_wh_val.lower() in g_env_map["Warehouse"]:
                    rt_dest_wh = g_env_map["Warehouse"][
                        dest_wh_val.lower()
                    ][env_name]

                    rt_dest_wh = rt_dest_wh.upper()

            ret_env_map['destination_warehouse'] = rt_dest_wh

        if 'source_database' in src_metameta:
            src_db_val = src_metameta['source_database']
            rt_src_db = src_db_val

            if (
                'source_type' in src_metameta and
                src_metameta['source_type'].lower() == "snowflake"
            ):
                if src_db_val.lower() in g_env_map["Database"]:
                    rt_src_db = g_env_map["Database"][
                        src_db_val.lower()
                    ][env_name]

                    rt_src_db = rt_src_db.upper()
            else:
                if (
                    'SQLDatabase' in g_env_map.keys() and
                    src_db_val.lower() in g_env_map["SQLDatabase"]
                ):
                    rt_src_db = g_env_map["SQLDatabase"][
                        src_db_val.lower()
                    ][env_name]

            ret_env_map['source_database'] = rt_src_db

        if 'outbound_database' in src_metameta:
            outbound_db_val = src_metameta['outbound_database']
            rt_outbound_db = outbound_db_val

            if outbound_db_val.lower() in g_env_map["Database"]:
                rt_outbound_db = g_env_map["Database"][
                    outbound_db_val.lower()
                ][env_name]

                rt_outbound_db = rt_outbound_db.upper()

            ret_env_map['outbound_database'] = rt_outbound_db
			
        if 'source_warehouse' in src_metameta:
            src_wh_val = src_metameta['source_warehouse']
            rt_src_wh = src_wh_val

            if (
                'source_type' in src_metameta and
                src_metameta['source_type'].lower() == "snowflake"
            ):
                if src_wh_val.lower() in g_env_map["Warehouse"]:
                    rt_src_wh = g_env_map["Warehouse"][
                        src_wh_val.lower()
                    ][env_name]

                    rt_src_wh = rt_src_wh.upper()

            ret_env_map['source_warehouse'] = rt_src_wh

        if 'archive_database' in src_metameta:
            archive_db_val = src_metameta['archive_database']
            rt_archive_db = archive_db_val

            if (
                'source_type' not in src_metameta or
                src_metameta['source_type'].lower() != "snowflake"
            ):
                if archive_db_val.lower() in g_env_map["Database"]:
                    rt_archive_db = g_env_map["Database"][
                        archive_db_val.lower()
                    ][env_name]

                    rt_archive_db = rt_archive_db.upper()

            ret_env_map['archive_database'] = rt_archive_db

        if 'root_folder' in src_metameta:
            rootfolder_val = src_metameta['root_folder'].lower()
            rt_rootfolder = rootfolder_val

            if (
                'root_folder' in g_env_map.keys() and
                rootfolder_val in g_env_map["root_folder"]
            ):
                rt_rootfolder = g_env_map["root_folder"][
                    rootfolder_val
                ][env_name]

            ret_env_map['root_folder'] = rt_rootfolder

        if 'post_execution_procedure' in src_metameta:
            ret_env_map['post_execution_procedure'] = (
                replace_db_in_procedurename_per_env(
                    src_metameta['post_execution_procedure'],
                    g_env_map["Database"],
                    env_name
                )
            )

        if 'ftp_root_folder' in src_metameta:
            ftp_root_folder_val = src_metameta['ftp_root_folder']
            rt_ftp_root_folder = ftp_root_folder_val

            if (
                'ftp_root_folder' in g_env_map.keys() and
                ftp_root_folder_val in g_env_map["ftp_root_folder"]
            ):
                rt_ftp_root_folder = g_env_map["ftp_root_folder"][
                    ftp_root_folder_val
                ][env_name]

            ret_env_map['ftp_root_folder'] = rt_ftp_root_folder
			
        if 'default_ftp_root_folder' in src_metameta:
            default_ftp_root_folder_val = src_metameta['default_ftp_root_folder']
            rt_default_ftp_root_folder = default_ftp_root_folder_val

            if (
                'default_ftp_root_folder' in g_env_map.keys() and
                default_ftp_root_folder_val in g_env_map['default_ftp_root_folder']
            ):
                rt_default_ftp_root_folder = g_env_map[
                    'default_ftp_root_folder'
                ][default_ftp_root_folder_val][env_name]

            ret_env_map['default_ftp_root_folder'] = (
                rt_default_ftp_root_folder
            )

        if 'ftp_host_name' in src_metameta:
            ftp_host_name_val = src_metameta['ftp_host_name'].lower()
            rt_ftp_host_name = ftp_host_name_val

            if 'ftp_host_name' in g_env_map.keys():
                if (
                    f'[{db_name}][{ftp_host_name_val}]'
                    in g_env_map['ftp_host_name']
                ):
                    rt_ftp_host_name = g_env_map['ftp_host_name'][
                        f'[{db_name}][{ftp_host_name_val}]'
                    ][env_name]
                elif ftp_host_name_val in g_env_map['ftp_host_name']:
                    rt_ftp_host_name = g_env_map['ftp_host_name'][
                        ftp_host_name_val
                    ][env_name]

            ret_env_map['ftp_host_name'] = rt_ftp_host_name

        if 'default_ftp_host_name' in src_metameta:
            default_ftp_host_name_val = (
                src_metameta['default_ftp_host_name'].lower()
            )
            rt_default_ftp_host_name = default_ftp_host_name_val

            if 'default_ftp_host_name' in g_env_map.keys():
                if (
                    f'[{db_name}][{default_ftp_host_name_val}]'
                    in g_env_map['default_ftp_host_name']
                ):
                    rt_default_ftp_host_name = g_env_map[
                        'default_ftp_host_name'
                    ][f'[{db_name}][{default_ftp_host_name_val}]'][env_name]

                elif (
                    default_ftp_host_name_val
                    in g_env_map['default_ftp_host_name']
                ):
                    rt_default_ftp_host_name = g_env_map[
                        'default_ftp_host_name'
                    ][default_ftp_host_name_val][env_name]

            ret_env_map['default_ftp_host_name'] = (
                rt_default_ftp_host_name
            )

        if 'to_uat' in src_metameta:
            to_uat_val = src_metameta['to_uat'].lower()
            rt_to_uat = to_uat_val

            if 'to_uat' in g_env_map.keys():
                if (
                    f'[{db_name}][{to_uat_val}]'
                    in g_env_map['to_uat']
                ):
                    rt_to_uat = g_env_map['to_uat'][
                        f'[{db_name}][{to_uat_val}]'
                    ][env_name]

                elif to_uat_val in g_env_map['to_uat']:
                    rt_to_uat = g_env_map['to_uat'][
                        to_uat_val
                    ][env_name]

            ret_env_map['to_uat'] = rt_to_uat
			
        if 'ftp_user_name' in src_metameta:
            ftp_user_name_val = src_metameta['ftp_user_name'].lower()
            rt_ftp_user_name = ftp_user_name_val

            if (
                'ftp_user_name' in g_env_map.keys() and
                ftp_user_name_val in g_env_map['ftp_user_name']
            ):
                rt_ftp_user_name = g_env_map['ftp_user_name'][
                    ftp_user_name_val
                ][env_name]

            ret_env_map['ftp_user_name'] = rt_ftp_user_name

        if 'default_ftp_user_name' in src_metameta:
            default_ftp_user_name_val = (
                src_metameta['default_ftp_user_name'].lower()
            )
            rt_default_ftp_user_name = default_ftp_user_name_val

            if (
                'default_ftp_user_name' in g_env_map.keys() and
                default_ftp_user_name_val in g_env_map['default_ftp_user_name']
            ):
                rt_default_ftp_user_name = g_env_map[
                    'default_ftp_user_name'
                ][default_ftp_user_name_val][env_name]

            ret_env_map['default_ftp_user_name'] = (
                rt_default_ftp_user_name
            )

        if 'uat_user_name' in src_metameta:
            uat_user_name_val = src_metameta['uat_user_name'].lower()
            rt_uat_user_name = uat_user_name_val

            if (
                'uat_user_name' in g_env_map.keys() and
                uat_user_name_val in g_env_map['uat_user_name']
            ):
                rt_uat_user_name = g_env_map['uat_user_name'][
                    uat_user_name_val
                ][env_name]

            ret_env_map['uat_user_name'] = rt_uat_user_name

        if 'uat_folder_path' in src_metameta:
            uat_folder_path_val = src_metameta['uat_folder_path']
            rt_uat_folder_path_val = uat_folder_path_val

            if (
                'uat_folder_path' in g_env_map.keys() and
                uat_folder_path_val in g_env_map['uat_folder_path']
            ):
                rt_uat_folder_path_val = g_env_map[
                    'uat_folder_path'
                ][uat_folder_path_val][env_name]

            ret_env_map['uat_folder_path'] = rt_uat_folder_path_val

        if 'hwm_server' in src_metameta:
            hwm_server_val = src_metameta['hwm_server'].lower()
            rt_hwm_server = hwm_server_val

            if (
                'hwm_server' in g_env_map.keys() and
                hwm_server_val in g_env_map['hwm_server']
            ):
                rt_hwm_server = g_env_map['hwm_server'][
                    hwm_server_val
                ][env_name]

            ret_env_map['hwm_server'] = rt_hwm_server

    return ret_env_map
	
def delete_blob(account_url, container, db_name1, type):
    metameta_blob_client = BlobClient.from_connection_string(
        account_url,
        container_name=container,
        blob_name=f"{db_name1}/{db_name1}{type}"
    )

    if metameta_blob_client.exists():
        metameta_blob_client.delete_blob()


def write_metameta(
    db_name: str,
    account_url: str,
    metameta_dict: dict,
    container: str
):
    # get metameta file
    metameta_blob_client = BlobClient.from_connection_string(
        account_url,
        container_name=container,
        blob_name=f"metadata/{db_name}/{db_name}_metameta.json"
    )

    dict_string = json.dumps(metameta_dict, indent=2)

    metameta_blob_client.upload_blob(
        dict_string,
        'BlockBlob',
        overwrite=True
    )

def split_write_metameta(
    db_name: str,
    account_url: str,
    metameta_dict: dict,
    container: str
):
    file_type_list = [
        '_dbmeta.json',
        '_metadata.json',
        '_metameta.json'
    ]

    chunked_list = []
    chunk_size = int(len(metameta_dict['entities']) / split_length)

    for i in range(
        0,
        len(metameta_dict['entities']),
        chunk_size
    ):
        chunked_list.append(
            metameta_dict['entities'][i:i + chunk_size]
        )

    config_length1 = config_length + 1

    for i in range(config_length1):
        if i == 0:
            for type in file_type_list:
                delete_blob(
                    account_url,
                    container,
                    db_name,
                    type
                )
        else:
            db_name1 = f"{db_name}_Set_{i}"

            for type in file_type_list:
                delete_blob(
                    account_url,
                    container,
                    db_name1,
                    type
                )

    for i in range(1, config_length):
        db_name1 = f"{db_name}_Set_{i}"
        metameta_dict_new = metameta_dict

        for j in range(0, len(chunked_list)):
            if (i - j) == 1:
                metameta_dict_new['entities'].clear()
                metameta_dict_new['entities'].extend(chunked_list[j])

                metameta_blob_client = BlobClient.from_connection_string(
                    account_url,
                    container_name=container,
                    blob_name=f"{db_name1}/{db_name1}_metameta.json"
                )

                dict_string = json.dumps(
                    metameta_dict_new,
                    indent=2
                )

                metameta_blob_client.upload_blob(
                    dict_string,
                    'BlockBlob',
                    overwrite=True
                )


def write_metameta_to_destination(
    db_name: str,
    account_url: str,
    metameta_dict: dict,
    container: str
):
    # get metameta file
    if (
        split_plandata_production == 'True' and
        db_name == 'plandata_Production'
    ):
        split_write_metameta(
            db_name,
            account_url,
            metameta_dict,
            container
        )
    else:
        metameta_blob_client = BlobClient.from_connection_string(
            account_url,
            container_name=container,
            blob_name=f"{db_name}/{db_name}_metameta.json"
        )

        dict_string = json.dumps(metameta_dict, indent=2)

        metameta_blob_client.upload_blob(
            dict_string,
            'BlockBlob',
            overwrite=True
        )


def write_hwm_value_to_db(
    server: str,
    db: str,
    db_hwm_values: dict
):
    for entity in db_hwm_values:
        ut.update_hwm_val_to_sql(
            server,
            db,
            entity,
            db_hwm_values[entity]
        )
		
def run_migrate_metameta(
    db_name: str,
    src_env: str,
    tgt_env: str,
    src_container: str,
    tgt_container: str,
    env_name: str
):
    src_metameta = get_src_metameta(
        db_name,
        src_env,
        src_container
    )

    if not src_metameta:
        logging.info(
            f"Nothing to process. Metameta for {db_name} not found."
        )
        return

    tgt_metameta = get_tgt_metameta(
        db_name,
        tgt_env,
        tgt_container
    )

    if not tgt_metameta:
        logging.info(
            f"There is no target metameta found for {db_name}."
        )

    env_map = get_environment_map(
        db_name,
        src_env,
        src_container,
        env_name,
        src_metameta
    )

    # STRY0019497: In case of automated-tests_* metameta files,
    # there has been no mapping needed.
    # This eventually returns empty "env_map" dictionary.
    # Hence, commenting below check.
    #
    # if not env_map:
    #     logging.info(
    #         f"Nothing to process. Environment map for {db_name} not found."
    #     )
    #     return

    if "source_server" in env_map:
        src_metameta['source_server'] = env_map['source_server']

    if "destination_database" in env_map:
        src_metameta['destination_database'] = \
            env_map['destination_database']

    if "destination_warehouse" in env_map:
        src_metameta['destination_warehouse'] = \
            env_map['destination_warehouse']

    if "source_database" in env_map:
        src_metameta['source_database'] = \
            env_map['source_database']

    if "outbound_database" in env_map:
        src_metameta['outbound_database'] = \
            env_map['outbound_database']

    if "source_warehouse" in env_map:
        src_metameta['source_warehouse'] = \
            env_map['source_warehouse']

    if "destination_server" in env_map:
        src_metameta['destination_server'] = \
            env_map['destination_server']

    if "external_stage_name" in src_metameta:
        src_metameta['external_stage_name'] = (
            f"{env_name.strip().upper()}_CSV_STAGE"
        )

    if "archive_database" in env_map:
        src_metameta['archive_database'] = env_map['archive_database']

    if "root_folder" in env_map:
        src_metameta['root_folder'] = env_map['root_folder']

    if "post_execution_procedure" in env_map:
        src_metameta['post_execution_procedure'] = \
            env_map['post_execution_procedure']

    if "ftp_root_folder" in env_map:
        src_metameta['ftp_root_folder'] = env_map['ftp_root_folder']

    if "default_ftp_root_folder" in env_map:
        src_metameta['default_ftp_root_folder'] = \
            env_map['default_ftp_root_folder']

    if "ftp_host_name" in env_map:
        src_metameta['ftp_host_name'] = env_map['ftp_host_name']

    if "default_ftp_host_name" in env_map:
        src_metameta['default_ftp_host_name'] = \
            env_map['default_ftp_host_name']

    if "ftp_user_name" in env_map:
        src_metameta['ftp_user_name'] = env_map['ftp_user_name']

    if "default_ftp_user_name" in env_map:
        src_metameta['default_ftp_user_name'] = \
            env_map['default_ftp_user_name']

    if "hwm_server" in env_map:
        src_metameta['hwm_server'] = env_map['hwm_server']

    if "to_uat" in env_map:
        src_metameta['to_uat'] = env_map['to_uat']

    if "uat_user_name" in env_map:
        src_metameta['uat_user_name'] = env_map['uat_user_name']
		
    if "uat_folder_path" in env_map:
        src_metameta['uat_folder_path'] = env_map['uat_folder_path']

    final_src_metameta_entities = list()

    if len(src_metameta['entities']) > 0:
        db_hwm_values = ut.get_hwm_val_from_sql(
            env_map['source_server'],
            src_metameta['source_database']
        )

        for src_entity in src_metameta['entities']:

            s_entity = src_entity["source_entity"]
            s_entity_lw = s_entity.lower()

            logging.info(f"Processing entity {s_entity}")

            # US35816: Source entities with past run_at date value have to be
            # excluded via CI/CD deployment to Metadata container
            if (
                "run_at" in src_entity.keys() and
                (
                    datetime.strptime(
                        src_entity["run_at"].strip(),
                        "%Y/%m/%d"
                    ).date()
                    <
                    datetime.now(
                        pytz.timezone('US/Pacific')
                    ).date()
                )
            ):
                logging.info(
                    f'{s_entity} has run_at value '
                    f'{src_entity["run_at"]} older than current date. '
                    f'Hence exclude it.'
                )
                continue

            if "destination_database" in src_entity:
                src_entity['destination_database'] = \
                    env_map['destination_database']

            if (
                ("delete_path" not in src_entity) or
                (
                    "delete_path" in src_entity and
                    src_entity["delete_path"] == "false"
                )
            ):
                if "delete_schedule" in src_entity:
                    del src_entity["delete_schedule"]

                if "soft_delete" in src_entity:
                    del src_entity["soft_delete"]

                if "delete_path" in src_entity:
                    del src_entity["delete_path"]

            if "destination_warehouse" in src_entity:
                src_entity['destination_warehouse'] = \
                    env_map['destination_warehouse']
		
            if "root_folder" in src_entity:
                env_map_keyvalue = get_environment_map_for_key(
                    db_name,
                    src_env,
                    src_container,
                    "root_folder"
                )

                rootfolder_val = src_entity['root_folder'].lower()
                rt_rootfolder = rootfolder_val

                if rootfolder_val in env_map_keyvalue.keys():
                    rt_rootfolder = env_map_keyvalue[
                        rootfolder_val
                    ][env_name]

                src_entity['root_folder'] = rt_rootfolder

            if "workspace_id" in src_entity:
                env_map_keyvalue = get_environment_map_for_key(
                    db_name,
                    src_env,
                    src_container,
                    "workspace_id"
                )

                workspace_id_val = src_entity['workspace_id'].lower()
                rt_workspace_id = workspace_id_val

                if workspace_id_val in env_map_keyvalue.keys():
                    rt_workspace_id = env_map_keyvalue[
                        workspace_id_val
                    ][env_name]

                src_entity['workspace_id'] = rt_workspace_id

            if "resource_id" in src_entity:
                env_map_keyvalue = get_environment_map_for_key(
                    db_name,
                    src_env,
                    src_container,
                    "resource_id"
                )

                resource_id_val = src_entity['resource_id'].lower()
                rt_resource_id = resource_id_val

                if resource_id_val in env_map_keyvalue.keys():
                    rt_resource_id = env_map_keyvalue[
                        resource_id_val
                    ][env_name]

                src_entity['resource_id'] = rt_resource_id

            if "hwm_col" not in src_entity and "hwm_id" not in src_entity:
                final_src_metameta_entities.append(src_entity)
                logging.info(f"{s_entity} does not have hwm_value")
                continue

            if (
                "hwm_col" in src_entity.keys() or
                "hwm_id" in src_entity.keys()
            ):
                if "hwm_col" in src_entity.keys():
                    hwm_value = reset_tgt_hwm

                elif "hwm_id" in src_entity.keys():
                    hwm_value = reset_tgt_hwm_id

                reset_hwm_value = hwm_value

                # US37306: Split plandata_Production_Set_2 metameta into 2 sets.
                # EDE1598: If source entity does not exist in target metameta,
                # however hwm_val exists in db i.e source entity has been already
                # synced to Snowflake, then retain hwm_val.
                if s_entity_lw in db_hwm_values:
                    hwm_value = db_hwm_values[s_entity_lw]
                    logging.info(
                        'hwm_val exists in db, Hence setting hwm_val as target'
                    )
                else:
                    logging.info(
                        'hwm_val does not exist in db, Hence hwm_val is reset'
                    )

                if tgt_metameta:
                    old_entity = find_entity_meta_meta(
                        tgt_metameta,
                        s_entity
                    )

                    if old_entity:
                        logging.info(
                            f"The {s_entity} exists in Target metameta."
                        )

                        if (
                            old_entity["merge_or_copy"] ==
                            src_entity["merge_or_copy"]
                        ):
                            if is_UK_HWM_match(
                                old_entity,
                                src_entity
                            ):
                                logging.info(
                                    f"merge_or_copy matched. "
                                    f"UKs matched for {s_entity}."
                                )
                            else:
                                hwm_value = reset_hwm_value
                                logging.info(
                                    f"merge_or_copy matched. "
                                    f"UKs do not match for {s_entity}. "
                                    f"Hence hwm_val is reset."
                                )
                        else:
                            hwm_value = reset_hwm_value
                            logging.info(
                                f"merge_or_copy has been changed for "
                                f"{s_entity}. Hence hwm_val is reset."
                            )

                    else:
                        logging.info(
                            f"The {s_entity} does not exist in "
                            f"Target metameta."
                        )

                else:
                    logging.info(
                        f"No Target metameta present for the {s_entity}."
                    )

                db_hwm_values[s_entity_lw] = hwm_value

                if "hwm_val" in src_entity:
                    del src_entity["hwm_val"]

            else:
                logging.info(
                    f"No hwm_val present in the {s_entity}. "
                    f"Hence skipping"
                )

            final_src_metameta_entities.append(src_entity)

            logging.info(
                f"Completed processing entity {s_entity}"
            )


        write_hwm_value_to_db(
            env_map['source_server'],
            src_metameta['source_database'],
            db_hwm_values
        )

    src_metameta['entities'] = final_src_metameta_entities

    logging.info(f"{'*' * 100}")
    logging.info(
        f"src_metameta: {len(src_metameta['entities'])} "
        f"is written to the destination"
    )
    logging.info(f"{'*' * 100}")

    write_metameta_to_destination(
        db_name,
        tgt_env,
        src_metameta,
        tgt_container
    )
