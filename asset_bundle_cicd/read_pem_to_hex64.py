import os
import sys
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.backends import default_backend

# pip install cryptography

def read_pem_to_hex64(file_path: str, password: str = None) -> str:
    """
    Reads a PEM private key file and returns the 64-character hex string.
    Supports 256-bit EC keys (e.g., secp256k1, prime256v1) and Ed25519 keys.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Key file not found: {file_path}")

    # Convert password to bytes if provided
    password_bytes = password.encode("utf-8") if password else None

    # Read the PEM file in binary mode
    with open(file_path, "rb") as key_file:
        pem_data = key_file.read()

    # Load the private key
    private_key = serialization.load_pem_private_key(
        pem_data,
        password=password_bytes,
        backend=default_backend()
    )

    # Case 1: Standard Elliptic Curve (secp256k1, P-256 / secp256r1)
    if isinstance(private_key, ec.EllipticCurvePrivateKey):
        private_int = private_key.private_numbers().private_value
        key_size_bytes = (private_key.curve.key_size + 7) // 8
        raw_bytes = private_int.to_bytes(key_size_bytes, byteorder="big")
        
    # Case 2: Ed25519 Keys
    elif isinstance(private_key, ed25519.Ed25519PrivateKey):
        raw_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    else:
        raise TypeError(f"Unsupported key type: {type(private_key).__name__}")

    hex_str = raw_bytes.hex()

    if len(hex_str) != 64:
        raise ValueError(
            f"Expected a 64-character hex string (32 bytes), but got {len(hex_str)} characters."
        )

    return hex_str


# Example execution
if __name__ == "__main__":
    pem_path = "private_key.pem"
    key_password = None  # Set to "your_password" if the PEM file is encrypted

    try:
        hex64_key = read_pem_to_hex64(pem_path, password=key_password)
        print("Hex64 Private Key:", hex64_key)
        print("Character Count  :", len(hex64_key))
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
