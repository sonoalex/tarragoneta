#!/usr/bin/env python
"""
Simple smoke test for storage providers.

Usage:
    python scripts/storage_test.py --file path/to/image.jpg [--key uploads/test.jpg]

What it does:
1) Carga la app Flask y obtiene el storage provider configurado (STORAGE_PROVIDER).
2) Sube el archivo usando storage.save(key, file_path).
3) Genera la URL pública con storage.url_for(key).
4) Hace un GET a la URL (si es http/https) y muestra el status y tamaño recibido.
"""

import argparse
import os
import sys
import requests

# Ensure project root is on path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


def main():
    parser = argparse.ArgumentParser(description="Storage smoke test (upload + fetch).")
    parser.add_argument("--file", required=True, help="Path to local file to upload")
    parser.add_argument("--key", default=None, help="Storage key/path (default: filename)")
    parser.add_argument(
        "--timeout", type=int, default=20, help="Timeout in seconds for GET request"
    )
    args = parser.parse_args()

    file_path = args.file
    if not os.path.isfile(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    key = args.key or os.path.basename(file_path)

    # Load Flask app and storage
    from app import create_app
    from app.storage import get_storage

    app = create_app()

    with app.app_context():
        storage = get_storage()
        provider = app.config.get("STORAGE_PROVIDER", "local")
        print(f"📦 STORAGE_PROVIDER={provider}")
        print(f"⬆️  Uploading {file_path} as key '{key}' ...")

        try:
            storage.save(key, file_path, delete_after_upload=False)
            print("✅ Upload successful")
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            sys.exit(1)

        try:
            url = storage.url_for(key)
            print(f"🔗 URL: {url}")
        except Exception as e:
            print(f"❌ Could not generate URL: {e}")
            sys.exit(1)

    # If URL is http/https, try to fetch it
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        try:
            print(f"🌐 GET {url} ...")
            resp = requests.get(url, timeout=args.timeout)
            size = len(resp.content) if resp and resp.content is not None else 0
            print(f"✅ GET status={resp.status_code}, bytes={size}")
            if resp.status_code != 200:
                print(f"⚠️ Body (first 200 chars): {resp.text[:200]}")
        except Exception as e:
            print(f"❌ GET failed: {e}")
    else:
        print("ℹ️ URL is not http/https; skipping GET")


if __name__ == "__main__":
    main()

