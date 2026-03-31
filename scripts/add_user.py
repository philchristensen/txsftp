#!/usr/bin/env python3
"""
Add or update an SFTP user in the txsftp database.

Usage:
    python scripts/add_user.py <username> <password> <home_directory>

Connects using the DB_* environment variables (same as docker-compose):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import os
import sys
import psycopg
from passlib.hash import des_crypt


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <username> <password> <home_directory>", file=sys.stderr)
        sys.exit(1)

    username, password, home_directory = sys.argv[1], sys.argv[2], sys.argv[3]
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

    print(f"User '{username}' created/updated with home '{home_directory}'.")


if __name__ == "__main__":
    main()
