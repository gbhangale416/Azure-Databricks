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

# Global configurations
reset_tgt_hwm = '1900/01/01'
reset_tgt_hwm_id = '0'
config_length = 10
split_length = 3
split_plandata_production = 'False'

# Configure baseline logging properties
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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

    if db_names and len(db_names.strip()) > 0:
        db_list = [db.strip() for db in db_names.split(",")]
    else:
        db_list = get_db_list(src_env, src_container)

    logging.info(f'Running for databases = {db_list}. total : {len(db_list)}')

    for db_name in db_list:
        logging.info(f"Processing db {db_name}")
        logging.info(f"db_name:, {src_env}, {tgt_env}, {src_container}, {tgt_container}, {env_name}")

        run_migrate_metameta(
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
            if len(tgt_entity["merge_check_cols"]) > 0 and len(src_entity["merge_check_cols"]) > 0:
                if (collections.Counter(tgt_entity["merge_check_cols"]) == 
                    collections.Counter(src_entity["merge_check_cols"]) and 
                    is_hwm_match(tgt_entity, src_entity)):
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
        return tgt_entity["hwm_col"] == src_entity["hwm_col"]

    if "hwm_id" in tgt_entity and "hwm_id" in src_entity:
        return tgt_entity["hwm_id"] == src_entity["hwm_id"]

    return False

	
def get_src_metameta(db_name: str, account_url: str, container: str):
    try:
        metameta_blob_client = BlobClient.from_connection_string(
            account_url,
            container_name=container,
            blob_name=f"metadata/{db_name}/{db_name}_metameta.json"
        )
        metameta_ssdl = metameta_blob_client.download_blob()
        return json.loads(metameta_ssdl.content_as_text())
    except Exception as e:
        logging.error(f"Source blob not found: {e}")
        return None


def read_merge_tgt_metameta(db_name: str, account_url: str, container: str):
    global config_length
    local_config_length = config_length + 1
    metameta_dict = dict()

    for i in range(0, local_config_length):
        if i == 0:
            metameta_blob_client = BlobClient.from_connection_string(
                account_url,
                container_name=container,
                blob_name=f"{db_name}/{db_name}_metameta.json"
            )
            if metameta_blob_client.exists():
                metameta_ssdl = metameta_blob_client.download_blob()
                metameta_dict_set = json.loads(metameta_ssdl.content_as_text())
                if metameta_dict_set is not None:
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
                metameta_dict_set = json.loads(metameta_ssdl.content_as_text())
                if len(metameta_dict) == 0:
                    metameta_dict.update(metameta_dict_set)
                else:
                    metameta_dict['entities'].extend(metameta_dict_set['entities'])

    return metameta_dict


def get_tgt_metameta(db_name: str, account_url: str, container: str):
    try:
        if split_plandata_production == 'True' and db_name == 'plandata_Production':
            metameta_dict = read_merge_tgt_metameta(db_name, account_url, container)
        else:
            metameta_blob_client = BlobClient.from_connection_string(
                account_url,
                container_name=container,
                blob_name=f"{db_name}/{db_name}_metameta.json"
            )
            metameta_ssdl = metameta_blob_client.download_blob()
            metameta_dict = json.loads(metameta_ssdl.content_as_text())
    except Exception as e:
        logging.error(f"Target blob not found: {e}")
        return None

    return metameta_dict


def replace_db_in_procedurename_per_env(procedure_name: str, env_map_database: dict, env: str):
    rt_procedure_name = procedure_name
    procedure_name_parts = procedure_name.strip().split('.')

    if len(procedure_name_parts) == 3:
        procedure_name_db_val = procedure_name_parts[0]
        if procedure_name_db_val.lower() in env_map_database.keys():
            rt_procedure_name_db = env_map_database[procedure_name_db_val.lower()][env]
            rt_procedure_name = f"{rt_procedure_name_db}.{procedure_name_parts[1]}.{procedure_name_parts[2]}"

    return rt_procedure_name.upper()


def get_db_environment_map(db_name: str, account_url: str, container: str):
    try:
        env_blob_client = BlobClient.from_connection_string(
            account_url,
            container_name=container,
            blob_name=f"metadata/{db_name}/{db_name}_environment_map.json"
        )
        env_ssdl = env_blob_client.download_blob()
        return json.loads(env_ssdl.content_as_text())
    except Exception as e:
        logging.error(f"Environment map not found in source: {e}")
        return None


def get_global_environment_map(db_name: str, account_url: str, container: str):
    try:
        env_blob_client = BlobClient.from_connection_string(
            account_url,
            container_name=container,
            blob_name="metadata/global_environment_map.json"
        )
        env_ssdl = env_blob_client.download_blob()
        return json.loads(env_ssdl.content_as_text())
    except Exception as e:
        logging.error(f"Global environment map not found in source: {e}")
        return None


# -----------------------------------------------------------------
# GENERIC ENVIRONMENT MAPPING CORE ENGINE (RECURSIVE & CONTEXT-AWARE)
# -----------------------------------------------------------------
def get_environment_map(db_name: str, account_url: str, container: str, env_name: str, src_metameta: dict):
    env_name_clean = env_name.strip()
    db_name_lower = db_name.lower() if db_name else ""

    # 1. Try DB-Specific Map First
    env_map = get_db_environment_map(db_name, account_url, container)
    if env_map:
        ret_env_map = {}
        for key in env_map.keys():
            if env_name_clean in env_map[key]:
                ret_env_map[key] = env_map[key][env_name_clean]
        return ret_env_map

    # 2. Fetch Global Environment Map
    g_env_map = get_global_environment_map(db_name, account_url, container)
    if not g_env_map:
        return {}

    # --- Rule Registries for Conditional Logic Checks ---
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
        
        # Priority Fallback List Builder
        lookups_to_try = []
        if db_name_lower and entity_name:
            lookups_to_try.append(f'[{db_name_lower}][{entity_name}][{val_lower}]') # [db][entity][value]
        if db_name_lower:
            lookups_to_try.append(f'[{db_name_lower}][{val_lower}]')               # [db][value]
        if entity_name:
            lookups_to_try.append(f'[{entity_name}][{val_lower}]')                   # [entity][value]
            
        lookups_to_try.extend([val_lower, val])                                      # value / original value

        pattern_categories = ['ftp_host_name', 'default_ftp_host_name', 'to_uat', 'default_ftp_root_folder', 'root_folder', 'workspace_id', 'resource_id']
        
        for category in pattern_categories:
            category_dict = g_env_map.get(category, g_env_map.get(category.lower(), {}))
            if isinstance(category_dict, dict):
                for lookup in lookups_to_try:
                    if lookup in category_dict:
                        return category_dict[lookup][env_name_clean]
        return val

    conditional_rules = {
        'destination_database': handle_destination_database,
        'destination_warehouse': handle_destination_warehouse,
        'source_database': handle_source_database,
        'source_warehouse': handle_source_warehouse,
        'ftp_host_name': handle_pattern_fields,
        'default_ftp_host_name': handle_pattern_fields,
        'to_uat': handle_pattern_fields,
        'default_ftp_root_folder': handle_pattern_fields,
        'root_folder': handle_pattern_fields,
        'workspace_id': handle_pattern_fields,
        'resource_id': handle_pattern_fields
    }

    # --- Recursive Replacement Mapping Mechanism ---
    def replace_recursively(node, current_key=None, parent_dict=None):
        if isinstance(node, dict):
            return {k: replace_recursively(v, current_key=k, parent_dict=node) for k, v in node.items()}
        elif isinstance(node, list):
            return [replace_recursively(item, current_key=current_key, parent_dict=parent_dict) for item in node]
        elif isinstance(node, str):
            if current_key in conditional_rules:
                return conditional_rules[current_key](node, context=parent_dict)
            if current_key == 'post_execution_procedure':
                return replace_db_in_procedurename_per_env(node, g_env_map.get("Database", {}), env_name_clean)
            
            # Pure Dynamic Fallback Value Scanner
            node_lower = node.lower()
            for category, mappings in g_env_map.items():
                if not isinstance(mappings, dict):
                    continue
                if node_lower in mappings:
                    resolved_val = mappings[node_lower][env_name_clean]
                    if current_key and any(x in current_key.lower() for x in ['database', 'warehouse']):
                        resolved_val = resolved_val.upper()
                    return resolved_val
                elif node in mappings:
                    return mappings[node][env_name_clean]
            return node
        return node

    return replace_recursively(src_metameta)


def delete_blob(account_url, container, db_name1, type):
    metameta_blob_client = BlobClient.from_connection_string(
        account_url,
        container_name=container,
        blob_name=f"{db_name1}/{db_name1}{type}"
    )
    if metameta_blob_client.exists():
        metameta_blob_client.delete_blob()


def write_metameta(db_name: str, account_url: str, metameta_dict: dict, container: str):
    metameta_blob_client = BlobClient.from_connection_string(
        account_url,
        container_name=container,
        blob_name=f"metadata/{db_name}/{db_name}_metameta.json"
    )
    dict_string = json.dumps(metameta_dict, indent=2)
    metameta_blob_client.upload_blob(dict_string, 'BlockBlob', overwrite=True)


def split_write_metameta(db_name: str, account_url: str, metameta_dict: dict, container: str):
    file_type_list = ['_dbmeta.json', '_metadata.json', '_metameta.json']
    chunked_list = []
    chunk_size = int(len(metameta_dict['entities']) / split_length)

    for i in range(0, len(metameta_dict['entities']), chunk_size):
        chunked_list.append(metameta_dict['entities'][i:i + chunk_size])

    global config_length
    config_length1 = config_length + 1

    for i in range(config_length1):
        if i == 0:
            for t in file_type_list:
                delete_blob(account_url, container, db_name, t)
        else:
            db_name1 = f"{db_name}_Set_{i}"
            for t in file_type_list:
                delete_blob(account_url, container, db_name1, t)

    for i in range(1, config_length):
        db_name1 = f"{db_name}_Set_{i}"
        metameta_dict_new = metameta_dict.copy()

        for j in range(0, len(chunked_list)):
            if (i - j) == 1:
                metameta_dict_new['entities'].clear()
                metameta_dict_new['entities'].extend(chunked_list[j])

                metameta_blob_client = BlobClient.from_connection_string(
                    account_url,
                    container_name=container,
                    blob_name=f"{db_name1}/{db_name1}_metameta.json"
                )
                dict_string = json.dumps(metameta_dict_new, indent=2)
                metameta_blob_client.upload_blob(dict_string, 'BlockBlob', overwrite=True)


def write_metameta_to_destination(db_name: str, account_url: str, metameta_dict: dict, container: str):
    if split_plandata_production == 'True' and db_name == 'plandata_Production':
        split_write_metameta(db_name, account_url, metameta_dict, container)
    else:
        metameta_blob_client = BlobClient.from_connection_string(
            account_url,
            container_name=container,
            blob_name=f"{db_name}/{db_name}_metameta.json"
        )
        dict_string = json.dumps(metameta_dict, indent=2)
        metameta_blob_client.upload_blob(dict_string, 'BlockBlob', overwrite=True)


def write_hwm_value_to_db(server: str, db: str, db_hwm_values: dict):
    for entity in db_hwm_values:
        ut.update_hwm_val_to_sql(server, db, entity, db_hwm_values[entity])


def run_migrate_metameta(db_name: str, src_env: str, tgt_env: str, src_container: str, tgt_container: str, env_name: str):
    # 1. Fetch Source Meta Configuration
    src_metameta = get_src_metameta(db_name, src_env, src_container)
    if not src_metameta:
        logging.info(f"Nothing to process. Metameta for {db_name} not found.")
        return

    # 2. Fetch Targeted Target Configuration
    tgt_metameta = get_tgt_metameta(db_name, tgt_env, tgt_container)
    if not tgt_metameta:
        logging.info(f"There is no target metameta found for {db_name}.")

    # 3. Dynamic Environment Translation Engine Core Call
    mapped_meta = get_environment_map(db_name, src_env, src_container, env_name, src_metameta)
    
    # In case get_environment_map returns full dynamic replacement tree directly
    if mapped_meta and isinstance(mapped_meta, dict) and 'entities' in mapped_meta:
        src_metameta = mapped_meta
    elif mapped_meta and isinstance(mapped_meta, dict):
        # Fallback to direct mapping properties updates
        for key, val in mapped_meta.items():
            if key != 'entities':
                src_metameta[key] = val

    # Static pipeline specific edge-case variables mapping handling
    if "external_stage_name" in src_metameta:
        src_metameta['external_stage_name'] = f"{env_name.strip().upper()}_CSV_STAGE"

    final_src_metameta_entities = list()

    if len(src_metameta['entities']) > 0:
        # Resolve target source_server & database parameters safely from translated layout structure
        resolved_server = src_metameta.get('source_server', '')
        resolved_db = src_metameta.get('source_database', '')
        
        db_hwm_values = ut.get_hwm_val_from_sql(resolved_server, resolved_db) if resolved_server and resolved_db else {}

        for src_entity in src_metameta['entities']:
            s_entity = src_entity["source_entity"]
            s_entity_lw = s_entity.lower()

            logging.info(f"Processing entity {s_entity}")

            # US35816: Active Run window validation logic filters execution criteria
            if "run_at" in src_entity.keys() and (
                datetime.strptime(src_entity["run_at"].strip(), "%Y/%m/%d").date() <
                datetime.now(pytz.timezone('US/Pacific')).date()
            ):
                logging.info(f'{s_entity} has run_at value {src_entity["run_at"]} older than current date. Excluded.')
                continue

            # Context aware dynamic remapping block for internal sub-elements inside Entity objects
            mapped_entity = get_environment_map(db_name, src_env, src_container, env_name, src_entity)
            if isinstance(mapped_entity, dict):
                src_entity.update(mapped_entity)

            # Cleanup soft-delete configurations structures
            if ("delete_path" not in src_entity) or ("delete_path" in src_entity and src_entity["delete_path"] == "false"):
                src_entity.pop("delete_schedule", None)
                src_entity.pop("soft_delete", None)
                src_entity.pop("delete_path", None)

            if "hwm_col" not in src_entity and "hwm_id" not in src_entity:
                final_src_metameta_entities.append(src_entity)
                logging.info(f"{s_entity} does not have hwm_value")
                continue

            if "hwm_col" in src_entity.keys() or "hwm_id" in src_entity.keys():
                hwm_value = reset_tgt_hwm if "hwm_col" in src_entity.keys() else reset_tgt_hwm_id
                reset_hwm_value = hwm_value

                if s_entity_lw in db_hwm_values:
                    hwm_value = db_hwm_values[s_entity_lw]
                    logging.info('hwm_val exists in db, Hence setting hwm_val as target')
                else:
                    logging.info('hwm_val does not exist in db, Hence hwm_val is reset')

                if tgt_metameta:
                    old_entity = find_entity_meta_meta(tgt_metameta, s_entity)
                    if old_entity:
                        logging.info(f"The {s_entity} exists in Target metameta.")
                        if old_entity["merge_or_copy"] == src_entity["merge_or_copy"]:
                            if is_UK_HWM_match(old_entity, src_entity):
                                logging.info(f"merge_or_copy matched. UKs matched for {s_entity}.")
                            else:
                                hwm_value = reset_hwm_value
                                logging.info(f"merge_or_copy matched. UKs do not match for {s_entity}. Resetting hwm_val.")
                        else:
                            hwm_value = reset_hwm_value
                            logging.info(f"merge_or_copy has been changed for {s_entity}. Resetting hwm_val.")
                    else:
                        logging.info(f"The {s_entity} does not exist in Target metameta.")
                else:
                    logging.info(f"No Target metameta present for the {s_entity}.")

                db_hwm_values[s_entity_lw] = hwm_value
                src_entity.pop("hwm_val", None)
            else:
                logging.info(f"No hwm_val present in the {s_entity}. Skipping")

            final_src_metameta_entities.append(src_entity)
            logging.info(f"Completed processing entity {s_entity}")

        if resolved_server and resolved_db:
            write_hwm_value_to_db(resolved_server, resolved_db, db_hwm_values)

    src_metameta['entities'] = final_src_metameta_entities

    logging.info(f"{'*' * 100}")
    logging.info(f"src_metameta: {len(src_metameta['entities'])} is written to the destination")
    logging.info(f"{'*' * 100}")

    write_metameta_to_destination(db_name, tgt_env, src_metameta, tgt_container)
