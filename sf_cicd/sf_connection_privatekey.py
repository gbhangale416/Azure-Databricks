import os
import re
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def get_snowflake_auth_private_key(privatekey=None):
    """
    Parses unencrypted PEM private key from a string or file path into PKCS8 DER bytes.
    Robust against Azure DevOps string interpolation that collapses newlines into spaces.
    """
    raw_key = privatekey or os.environ.get("SF_PRIVATE_KEY")
    if not raw_key:
        raise ValueError("Private key is empty. Ensure SF_PRIVATE_KEY is provided.")

    # If passed a file path that exists on the agent
    if os.path.isfile(raw_key):
        with open(raw_key, "rb") as kf:
            key_bytes = kf.read()
            return serialization.load_pem_private_key(
                key_bytes, password=None, backend=default_backend()
            ).private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

    # Clean surrounding quotes and whitespace
    clean_key = raw_key.strip().strip("'").strip('"')

    # Convert literal "\n" strings into actual newline characters
    if "\\n" in clean_key:
        clean_key = clean_key.replace("\\n", "\n")

    # If Azure DevOps collapsed newlines into single spaces, reconstruct the PEM structure
    if "\n" not in clean_key:
        pattern = r"(-----BEGIN [A-Z ]+-----)\s+(.+)\s+(-----END [A-Z ]+-----)"
        match = re.search(pattern, clean_key)
        if match:
            header, body, footer = match.groups()
            body_no_spaces = body.replace(" ", "")
            # Split base64 payload into standard 64-char lines
            body_lines = [
                body_no_spaces[i : i + 64]
                for i in range(0, len(body_no_spaces), 64)
            ]
            clean_key = f"{header}\n" + "\n".join(body_lines) + f"\n{footer}\n"

    pem_bytes = clean_key.encode("utf-8")

    private_key_obj = serialization.load_pem_private_key(
        pem_bytes, password=None, backend=default_backend()
    )

    return private_key_obj.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_snowflake_connection(
    user,
    account,
    role,
    warehouse,
    database,
    authenticator="snowflake",
    password=None,
    use_key_pair=False,
    sf_private_key=None,
):
    """
    Establishes a Snowflake connection using Key-Pair or Password authentication.
    """
    conn_params = {
        "user": user,
        "account": account,
        "role": role,
        "warehouse": warehouse,
        "database": database,
        "authenticator": authenticator,
    }

    if use_key_pair:
        conn_params["private_key"] = get_snowflake_auth_private_key(
            sf_private_key
        )
    else:
        pwd = password or os.environ.get("SNOWSQL_PWD")
        if not pwd:
            raise ValueError(
                "Password must be provided when use_key_pair is False."
            )
        conn_params["password"] = pwd

    return snowflake.connector.connect(**conn_params)
