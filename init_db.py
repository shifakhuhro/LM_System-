#!/usr/bin/env python3
"""
init_db.py — One-time database initialisation script.

Usage:
    python init_db.py

This script:
1. Reads schema.sql and creates all tables (idempotent).
2. Inserts the default librarian account with a properly-hashed password.
   Default credentials: admin@library.com / admin123

Set environment variables (or edit config.py) to match your MySQL setup:
  MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
"""

import pymysql
from werkzeug.security import generate_password_hash
from config import Config
import os

DB_INIT_SQL = os.path.join(os.path.dirname(__file__), 'schema.sql')

ADMIN_NAME     = 'Admin Librarian'
ADMIN_EMAIL    = 'admin@library.com'
ADMIN_PASSWORD = 'admin123'


def run():
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        charset='utf8mb4',
        autocommit=True,
    )
    with conn.cursor() as cur:
        # Create database if not exists
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cur.execute(f"USE `{Config.MYSQL_DB}`")

        # Execute schema
        with open(DB_INIT_SQL, 'r') as f:
            sql = f.read()

        # Split on semicolons and run each statement
        for statement in sql.split(';'):
            stmt = statement.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    cur.execute(stmt)
                except Exception as e:
                    print(f"  Skipped: {e}")

        # Upsert admin with proper password hash
        hashed = generate_password_hash(ADMIN_PASSWORD)
        cur.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (%s, %s, %s, 'librarian')
            ON DUPLICATE KEY UPDATE password = VALUES(password), name = VALUES(name)
        """, (ADMIN_NAME, ADMIN_EMAIL, hashed))

    conn.close()
    print("Database initialised successfully.")
    print(f"  Librarian login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == '__main__':
    run()
