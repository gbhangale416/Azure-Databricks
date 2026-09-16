import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import snowflake.connector


def _get_private_key_bytes(private_key_data, passphrase=None):
    """Parses a PEM private key file path or raw string into PKCS8 DER bytes."""
    if os.path.exists(private_key_data):
        with open(private_key_data, "rb") as key_file:
            key_bytes = key_file.read()
    else:
        key_bytes = private_key_data.replace("\\n", "\n").strip().encode("utf-8")

    password_bytes = passphrase.encode("utf-8") if passphrase else None
    p_key = serialization.load_pem_private_key(
        key_bytes,
        password=password_bytes,
        backend=default_backend(),
    )

    return p_key.private_bytes(
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
    authenticator,
    password=None,
    use_key_pair=False,
    sf_private_key=None,
    private_key_passphrase=None,
):
    conn_params = {
        "user": user,
        "account": account,
        "role": role,
        "warehouse": warehouse,
        "database": database,
        "authenticator": authenticator,
    }

    if use_key_pair:
        if not sf_private_key:
            raise ValueError(
                "sf_private_key must be provided when use_key_pair is True."
            )
        conn_params["private_key"] = _get_private_key_bytes(
            sf_private_key, private_key_passphrase
        )
    else:
        if not password:
            raise ValueError(
                "password must be provided when use_key_pair is False."
            )
        conn_params["password"] = password

    return snowflake.connector.connect(**conn_params)
