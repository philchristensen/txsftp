#!/usr/bin/env python3
"""
Create or update an SFTP user in the txsftp database.

Usage:
    python scripts/upsert_user.py <username> <password> [home_directory]

Home directory must be under /data/sftp/ and defaults to /data/sftp/<username>.

Connects using the DB_* environment variables (same as docker-compose):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import os
import sys
import psycopg
from passlib.hash import des_crypt


def main():
    if len(sys.argv) not in (3, 4):
        print(f"Usage: {sys.argv[0]} <username> <password> [home_directory]", file=sys.stderr)
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    home_directory = sys.argv[3] if len(sys.argv) == 4 else f'/data/sftp/{username}'

    if not home_directory.startswith('/data/sftp/'):
        print(f"Error: home directory must be under /data/sftp/ (got '{home_directory}')", file=sys.stderr)
        sys.exit(1)

    password_hash = des_crypt.hash(password)

    conn_str = (
        f"host={os.environ.get('DB_HOST', 'localhost')} "
        f"port={os.environ.get('DB_PORT', '5432')} "
        f"dbname={os.environ.get('DB_NAME', 'txsftp')} "
        f"user={os.environ.get('DB_USER', 'txsftp')} "
        f"password={os.environ.get('DB_PASSWORD', 'txsftp')}"
    )

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sftp_user (username, password, home_directory)
                VALUES (%s, %s, %s)
                ON CONFLICT (username) DO UPDATE
                    SET password = EXCLUDED.password,
                        home_directory = EXCLUDED.home_directory
                """,
                (username, password_hash, home_directory),
            )
        conn.commit()

    print(f"User '{username}' upserted with home '{home_directory}'.")


if __name__ == "__main__":
    main()
