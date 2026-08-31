import os
import sys
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.hazmat.backends import default_backend


def read_pem_to_hex(file_path: str, password: str = None) -> str:
    """
    Reads an EC, Ed25519, or RSA PEM private key and returns its raw private key in hex.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Key file not found: {file_path}")

    password_bytes = password.encode("utf-8") if password else None

    with open(file_path, "rb") as key_file:
        pem_data = key_file.read()

    private_key = serialization.load_pem_private_key(
        pem_data,
        password=password_bytes,
        backend=default_backend()
    )

    # 1. RSA Private Key (Extracts private exponent 'd')
    if isinstance(private_key, rsa.RSAPrivateKey):
        d_val = private_key.private_numbers().d
        key_size_bytes = (private_key.key_size + 7) // 8
        raw_bytes = d_val.to_bytes(key_size_bytes, byteorder="big")

    # 2. Elliptic Curve (secp256k1, P-256, etc.)
    elif isinstance(private_key, ec.EllipticCurvePrivateKey):
        private_int = private_key.private_numbers().private_value
        key_size_bytes = (private_key.curve.key_size + 7) // 8
        raw_bytes = private_int.to_bytes(key_size_bytes, byteorder="big")

    # 3. Ed25519
    elif isinstance(private_key, ed25519.Ed25519PrivateKey):
        raw_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    else:
        raise TypeError(f"Unsupported key type: {type(private_key).__name__}")

    return raw_bytes.hex()


if __name__ == "__main__":
    pem_path = "private_key.pem"
    key_password = None  # Add password if PEM is encrypted

    try:
        hex_key = read_pem_to_hex(pem_path, password=key_password)
        print("Hex Private Key :", hex_key)
        print("Character Count :", len(hex_key))
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
