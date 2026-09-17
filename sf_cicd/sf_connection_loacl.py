import base64
import snowflake.connector
from cryptography.hazmat.primitives import serialization


def get_snowflake_auth_private_key(private_key):
    private_key_pem_str = base64.b64decode(private_key).decode("utf-8")
    private_key_pem = private_key_pem_str.encode("utf-8")

    private_key_obj = serialization.load_pem_private_key(
        private_key_pem,
        password=None
    )

    private_key_der = private_key_obj.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    return private_key_der


def get_snowflake_connection(password, use_key_pair, sf_private_key):

    conn_params = {
        "user": "",
        "account": "",
        "role": "",
        "warehouse": "",
        "database": "",
        "authenticator": "",
    }

    if use_key_pair:
        if not sf_private_key:
            raise ValueError(
                "sf_private_key must be provided when use_key_pair is True."
            )

        conn_params["private_key"] = get_snowflake_auth_private_key(
            sf_private_key
        )

    else:
        if not password:
            raise ValueError(
                "password must be provided when use_key_pair is False."
            )

        conn_params["password"] = password

    return snowflake.connector.connect(**conn_params)


# ============================================================
# RUN CODE
# ============================================================

if __name__ == "__main__":

    # Your Base64 encoded private key
    sf_private_key = "<BASE64_ENCODED_PRIVATE_KEY>"

    try:
        conn = get_snowflake_connection(
            password=None,
            use_key_pair=True,
            sf_private_key=sf_private_key
        )

        print("Snowflake connection successful")

        # Test query
        cursor = conn.cursor()

        cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE()")

        result = cursor.fetchone()

        print("User     :", result[0])
        print("Role     :", result[1])
        print("Database :", result[2])

        cursor.close()
        conn.close()

        print("Snowflake connection closed")

    except Exception as e:
        print(f"Snowflake connection failed: {e}")
